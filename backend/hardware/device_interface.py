#!/usr/bin/env python3
"""
FIRM-LOCK Hardware Device Interface
Handles communication with STM32 + ATECC608A device via USB/Serial
"""

import serial
import serial.tools.list_ports
import struct
import time
import hashlib
import secrets
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class DeviceResponse:
    """Response from hardware device"""
    success: bool
    data: bytes
    error: Optional[str] = None


@dataclass
class AttestationEvidence:
    """Attestation evidence from device"""
    device_id: str
    nonce: bytes
    timestamp: int
    pcrs: Dict[int, bytes]
    signature: bytes
    certificate: bytes


class DeviceInterface:
    """
    Interface to FIRM-LOCK hardware device
    
    Protocol:
    - USB CDC-ACM serial communication
    - Binary packet format with CRC32 checksum
    - Commands:
      * 0x01: GET_DEVICE_INFO
      * 0x02: GET_PCRS
      * 0x03: ATTESTATION_CHALLENGE
      * 0x04: TRIGGER_RECOVERY
      * 0x05: GET_FIRMWARE_VERSION
    """
    
    # Protocol constants
    PACKET_START = 0xFA
    PACKET_END = 0xFB
    CMD_GET_INFO = 0x01
    CMD_GET_PCRS = 0x02
    CMD_ATTEST = 0x03
    CMD_RECOVER = 0x04
    CMD_GET_VERSION = 0x05
    
    # Response codes
    RESP_OK = 0x00
    RESP_ERROR = 0x01
    RESP_INVALID_CMD = 0x02
    RESP_BUSY = 0x03
    
    def __init__(self, port: Optional[str] = None, baudrate: int = 115200):
        """
        Initialize device interface
        
        Args:
            port: Serial port (auto-detect if None)
            baudrate: Serial baudrate (default 115200)
        """
        self.port = port
        self.baudrate = baudrate
        self.serial: Optional[serial.Serial] = None
        self.timeout = 5.0
        
    def find_device(self) -> Optional[str]:
        """
        Auto-detect FIRM-LOCK device port
        
        Returns:
            Port name if found, None otherwise
        """
        print("[HARDWARE] Searching for FIRM-LOCK device...")
        
        # List all serial ports
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            # Check for common USB-to-serial chips and STM32
            if any(vid in port.hwid for vid in [
                "VID:PID=0483",  # STMicroelectronics (STM32)
                "VID:PID=2341",  # Arduino
                "VID:PID=1A86",  # CH340
                "VID:PID=10C4",  # CP210x
                "VID:PID=067B",  # Prolific
            ]):
                print(f"[HARDWARE] Found potential device: {port.device} ({port.description})")
                return port.device
                
        # Fallback: try common port names
        for port_name in ["/dev/ttyACM0", "/dev/ttyUSB0", "/dev/tty.usbmodem*", "COM3", "COM4"]:
            try:
                s = serial.Serial(port_name, self.baudrate, timeout=1)
                s.close()
                print(f"[HARDWARE] Found device at: {port_name}")
                return port_name
            except:
                continue
                
        print("[HARDWARE] No device found")
        return None
        
    def connect(self) -> bool:
        """
        Connect to hardware device
        
        Returns:
            True if connected, False otherwise
        """
        if self.port is None:
            self.port = self.find_device()
            
        if self.port is None:
            print("[HARDWARE] ERROR: No device found")
            return False
            
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            
            # Wait for device to initialize
            time.sleep(0.5)
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            
            print(f"[HARDWARE] Connected to {self.port} at {self.baudrate} baud")
            return True
            
        except serial.SerialException as e:
            print(f"[HARDWARE] ERROR: Failed to connect: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from device"""
        if self.serial:
            self.serial.close()
            self.serial = None
            print("[HARDWARE] Disconnected")
            
    def is_connected(self) -> bool:
        """Check if device is connected"""
        return self.serial is not None and self.serial.is_open
        
    def _calculate_crc32(self, data: bytes) -> int:
        """Calculate CRC32 checksum"""
        return hashlib.crc32(data) & 0xFFFFFFFF
        
    def _send_command(self, cmd: int, data: bytes = b"") -> DeviceResponse:
        """
        Send command to device and receive response
        
        Args:
            cmd: Command byte
            data: Command data
            
        Returns:
            DeviceResponse with result
        """
        if not self.is_connected():
            return DeviceResponse(False, b"", "Not connected")
            
        # Build packet
        length = len(data)
        crc = self._calculate_crc32(struct.pack("<B", cmd) + data)
        
        packet = struct.pack("<BBH", self.PACKET_START, cmd, length) + data
        packet += struct.pack("<I", crc)
        packet += struct.pack("<B", self.PACKET_END)
        
        # Send packet
        try:
            self.serial.write(packet)
            self.serial.flush()
        except serial.SerialException as e:
            return DeviceResponse(False, b"", f"Send error: {e}")
            
        # Read response
        try:
            # Read header (start byte + response code + length)
            header = self.serial.read(4)
            if len(header) < 4:
                return DeviceResponse(False, b"", "Timeout waiting for response")
                
            start, resp_code, length = struct.unpack("<BBH", header)
            
            if start != self.PACKET_START:
                return DeviceResponse(False, b"", "Invalid response start byte")
                
            # Read data
            data = self.serial.read(length) if length > 0 else b""
            
            # Read CRC and end byte
            trailer = self.serial.read(5)
            if len(trailer) < 5:
                return DeviceResponse(False, b"", "Incomplete response")
                
            crc_received = struct.unpack("<I", trailer[:4])[0]
            end = trailer[4]
            
            if end != self.PACKET_END:
                return DeviceResponse(False, b"", "Invalid response end byte")
                
            # Verify CRC
            crc_calculated = self._calculate_crc32(struct.pack("<B", resp_code) + data)
            if crc_received != crc_calculated:
                return DeviceResponse(False, b"", "CRC mismatch")
                
            if resp_code == self.RESP_OK:
                return DeviceResponse(True, data)
            else:
                return DeviceResponse(False, data, f"Device error: {resp_code}")
                
        except serial.SerialException as e:
            return DeviceResponse(False, b"", f"Receive error: {e}")
            
    def get_device_info(self) -> Dict:
        """
        Get device information
        
        Returns:
            Device info dict
        """
        resp = self._send_command(self.CMD_GET_INFO)
        
        if not resp.success:
            return {"error": resp.error}
            
        # Parse response
        # Format: device_id (16 bytes) | firmware_major (1) | firmware_minor (1) | firmware_patch (1)
        if len(resp.data) < 19:
            return {"error": "Invalid response length"}
            
        device_id = resp.data[:16].decode('ascii').strip('\x00')
        major, minor, patch = struct.unpack("<BBB", resp.data[16:19])
        
        return {
            "device_id": device_id,
            "firmware_version": f"v{major}.{minor}.{patch}",
            "connected": True
        }
        
    def get_pcrs(self) -> Dict[int, bytes]:
        """
        Get PCR values from device
        
        Returns:
            Dict mapping PCR index to 32-byte hash
        """
        resp = self._send_command(self.CMD_GET_PCRS)
        
        if not resp.success:
            return {}
            
        # Parse response: 4 PCRs, each 32 bytes
        pcrs = {}
        for i in range(4):
            offset = i * 32
            if offset + 32 <= len(resp.data):
                pcrs[i] = resp.data[offset:offset+32]
                
        return pcrs
        
    def send_attestation_challenge(self, nonce: bytes) -> Optional[AttestationEvidence]:
        """
        Send attestation challenge to device
        
        Args:
            nonce: 32-byte random nonce
            
        Returns:
            AttestationEvidence if successful, None otherwise
        """
        # Build challenge data: nonce (32) + timestamp (4)
        timestamp = int(time.time())
        challenge_data = nonce + struct.pack("<I", timestamp)
        
        resp = self._send_command(self.CMD_ATTEST, challenge_data)
        
        if not resp.success:
            print(f"[HARDWARE] Attestation failed: {resp.error}")
            return None
            
        # Parse response
        # Format: device_id (16) | nonce (32) | timestamp (4) | 
        #         pcr0 (32) | pcr1 (32) | pcr2 (32) | pcr3 (32) |
        #         signature (64) | certificate (128)
        
        offset = 0
        device_id = resp.data[offset:offset+16].decode('ascii').strip('\x00')
        offset += 16
        
        resp_nonce = resp.data[offset:offset+32]
        offset += 32
        
        resp_timestamp = struct.unpack("<I", resp.data[offset:offset+4])[0]
        offset += 4
        
        pcrs = {}
        for i in range(4):
            pcrs[i] = resp.data[offset:offset+32]
            offset += 32
            
        signature = resp.data[offset:offset+64]
        offset += 64
        
        certificate = resp.data[offset:offset+128]
        
        return AttestationEvidence(
            device_id=device_id,
            nonce=resp_nonce,
            timestamp=resp_timestamp,
            pcrs=pcrs,
            signature=signature,
            certificate=certificate
        )
        
    def trigger_recovery(self) -> bool:
        """
        Trigger golden image recovery
        
        Returns:
            True if successful
        """
        resp = self._send_command(self.CMD_RECOVER)
        return resp.success
        
    def get_firmware_version(self) -> str:
        """
        Get firmware version
        
        Returns:
            Version string
        """
        resp = self._send_command(self.CMD_GET_VERSION)
        
        if not resp.success or len(resp.data) < 3:
            return "unknown"
            
        major, minor, patch = struct.unpack("<BBB", resp.data[:3])
        return f"v{major}.{minor}.{patch}"


# ============================================================================
# SIMULATION MODE
# ============================================================================

class SimulatedDeviceInterface(DeviceInterface):
    """Simulated device interface for testing without hardware"""
    
    def __init__(self):
        self._connected = False
        self._device_id = "FL-2847-AF"
        self._firmware_version = (2, 1, 0)
        self._pcrs = {
            0: bytes.fromhex("7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b"),
            1: bytes.fromhex("a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2"),
            2: bytes.fromhex("d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5"),
            3: bytes.fromhex("9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b")
        }
        self._golden_pcrs = self._pcrs.copy()
        self._compromised = False
        
    def find_device(self) -> Optional[str]:
        return "SIMULATED"
        
    def connect(self) -> bool:
        print("[SIMULATION] Connected to simulated device")
        self._connected = True
        return True
        
    def disconnect(self):
        self._connected = False
        print("[SIMULATION] Disconnected")
        
    def is_connected(self) -> bool:
        return self._connected
        
    def get_device_info(self) -> Dict:
        return {
            "device_id": self._device_id,
            "firmware_version": f"v{self._firmware_version[0]}.{self._firmware_version[1]}.{self._firmware_version[2]}",
            "connected": True,
            "simulated": True
        }
        
    def get_pcrs(self) -> Dict[int, bytes]:
        return self._pcrs.copy()
        
    def send_attestation_challenge(self, nonce: bytes) -> Optional[AttestationEvidence]:
        import time
        
        # Simulate processing delay
        time.sleep(0.5)
        
        return AttestationEvidence(
            device_id=self._device_id,
            nonce=nonce,
            timestamp=int(time.time()),
            pcrs=self._pcrs.copy(),
            signature=secrets.token_bytes(64),
            certificate=secrets.token_bytes(128)
        )
        
    def trigger_recovery(self) -> bool:
        # Restore golden PCRs
        self._pcrs = self._golden_pcrs.copy()
        self._compromised = False
        time.sleep(1)
        return True
        
    def simulate_attack(self):
        """Simulate firmware attack (for demo)"""
        # Modify PCR[1] to simulate compromised application
        self._pcrs[1] = bytes.fromhex("e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6")
        self._compromised = True
        
    def get_firmware_version(self) -> str:
        return f"v{self._firmware_version[0]}.{self._firmware_version[1]}.{self._firmware_version[2]}"


# Factory function
def create_device_interface(simulated: bool = False) -> DeviceInterface:
    """
    Create appropriate device interface
    
    Args:
        simulated: Use simulated interface if True
        
    Returns:
        DeviceInterface instance
    """
    if simulated:
        return SimulatedDeviceInterface()
    else:
        return DeviceInterface()


# ============================================================================
# MAIN (for testing)
# ============================================================================

if __name__ == "__main__":
    print("FIRM-LOCK Hardware Interface Test")
    print("=" * 50)
    
    # Try to connect to real device, fall back to simulation
    device = create_device_interface(simulated=False)
    
    if not device.connect():
        print("\nFalling back to simulation mode...")
        device = create_device_interface(simulated=True)
        device.connect()
        
    # Get device info
    info = device.get_device_info()
    print(f"\nDevice Info: {info}")
    
    # Get PCRs
    pcrs = device.get_pcrs()
    print(f"\nPCR Values:")
    for i, pcr in pcrs.items():
        print(f"  PCR[{i}]: {pcr.hex()[:32]}...")
        
    # Test attestation
    print("\nTesting attestation...")
    nonce = secrets.token_bytes(32)
    evidence = device.send_attestation_challenge(nonce)
    
    if evidence:
        print(f"  Device ID: {evidence.device_id}")
        print(f"  Timestamp: {evidence.timestamp}")
        print(f"  Signature: {evidence.signature.hex()[:32]}...")
        
    device.disconnect()
