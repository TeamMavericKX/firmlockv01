#!/usr/bin/env python3
"""
FIRM-LOCK Backend API
FastAPI-based backend for device attestation and fleet management
"""

import asyncio
import json
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Import hardware interface (simulated mode if no hardware)
try:
    from hardware.device_interface import DeviceInterface
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("[WARNING] Hardware interface not available - running in SIMULATION mode")


# ============================================================================
# DATA MODELS
# ============================================================================

class DeviceInfo(BaseModel):
    device_id: str
    status: str = "healthy"  # healthy, compromised, quarantine, offline
    firmware_version: str
    last_attestation: Optional[str] = None
    uptime_seconds: int = 0
    pcrs: Dict[int, str] = {}
    
class AttestationChallenge(BaseModel):
    nonce: str
    timestamp: int
    device_id: str

class AttestationEvidence(BaseModel):
    device_id: str
    nonce: str
    timestamp: int
    pcrs: Dict[int, str]
    signature: str
    certificate: str

class AttestationResult(BaseModel):
    result: str  # PASS, FAIL, QUARANTINE
    reason: Optional[str] = None
    timestamp: str
    latency_ms: float
    pcr_match: Dict[int, bool]

class FirmwareInfo(BaseModel):
    version: str
    security_counter: int
    hash: str
    signature: str


# ============================================================================
# IN-MEMORY DATABASE (Replace with PostgreSQL in production)
# ============================================================================

class Database:
    def __init__(self):
        self.devices: Dict[str, DeviceInfo] = {}
        self.attestation_logs: List[Dict] = []
        self.golden_pcrs: Dict[str, Dict[int, str]] = {}
        self.used_nonces: Set[str] = set()
        self.firmware_db: Dict[str, FirmwareInfo] = {}
        
    def init_demo_data(self):
        """Initialize with demo device"""
        demo_device = DeviceInfo(
            device_id="FL-2847-AF",
            status="healthy",
            firmware_version="v2.1.0",
            last_attestation=datetime.now().isoformat(),
            uptime_seconds=4060800,  # 47 days
            pcrs={
                0: "0x7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b",
                1: "0xa1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
                2: "0xd4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5",
                3: "0x9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b"
            }
        )
        self.devices["FL-2847-AF"] = demo_device
        self.golden_pcrs["FL-2847-AF"] = demo_device.pcrs.copy()
        
        # Add some attestation logs
        self.attestation_logs = [
            {
                "time": (datetime.now() - timedelta(minutes=2)).strftime("%H:%M:%S"),
                "type": "Scheduled",
                "result": "PASS",
                "device_id": "FL-2847-AF"
            },
            {
                "time": (datetime.now() - timedelta(minutes=17)).strftime("%H:%M:%S"),
                "type": "Manual",
                "result": "PASS",
                "device_id": "FL-2847-AF"
            },
            {
                "time": (datetime.now() - timedelta(minutes=47)).strftime("%H:%M:%S"),
                "type": "Scheduled",
                "result": "PASS",
                "device_id": "FL-2847-AF"
            }
        ]

db = Database()
db.init_demo_data()


# ============================================================================
# WEBSOCKET CONNECTION MANAGER
# ============================================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WEBSOCKET] Client connected. Total: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[WEBSOCKET] Client disconnected. Total: {len(self.active_connections)}")
        
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"[WEBSOCKET] Error broadcasting: {e}")
                
    async def send_to(self, websocket: WebSocket, message: dict):
        """Send message to specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"[WEBSOCKET] Error sending: {e}")

manager = ConnectionManager()


# ============================================================================
# ATTESTATION ENGINE
# ============================================================================

class AttestationEngine:
    def __init__(self):
        self.challenge_timeout = 60  # seconds
        
    def generate_challenge(self, device_id: str) -> AttestationChallenge:
        """Generate a new attestation challenge"""
        nonce = secrets.token_hex(32)  # 64 character hex string
        timestamp = int(time.time())
        
        # Track nonce
        db.used_nonces.add(nonce)
        
        return AttestationChallenge(
            nonce=nonce,
            timestamp=timestamp,
            device_id=device_id
        )
    
    def verify_evidence(self, evidence: AttestationEvidence, challenge: AttestationChallenge) -> AttestationResult:
        """Verify attestation evidence against challenge"""
        start_time = time.time()
        
        # Check nonce matches
        if evidence.nonce != challenge.nonce:
            return AttestationResult(
                result="FAIL",
                reason="NONCE_MISMATCH",
                timestamp=datetime.now().isoformat(),
                latency_ms=(time.time() - start_time) * 1000,
                pcr_match={}
            )
        
        # Check timestamp freshness
        current_time = int(time.time())
        if current_time - evidence.timestamp > self.challenge_timeout:
            return AttestationResult(
                result="FAIL",
                reason="CHALLENGE_EXPIRED",
                timestamp=datetime.now().isoformat(),
                latency_ms=(time.time() - start_time) * 1000,
                pcr_match={}
            )
        
        # Check nonce hasn't been reused
        if evidence.nonce not in db.used_nonces:
            return AttestationResult(
                result="FAIL",
                reason="REPLAY_DETECTED",
                timestamp=datetime.now().isoformat(),
                latency_ms=(time.time() - start_time) * 1000,
                pcr_match={}
            )
        
        # Compare PCRs against golden values
        golden = db.golden_pcrs.get(evidence.device_id, {})
        pcr_match = {}
        all_match = True
        
        for i in range(4):
            expected = golden.get(i, "")
            received = evidence.pcrs.get(i, "")
            matches = expected == received
            pcr_match[i] = matches
            if not matches:
                all_match = False
        
        # Determine result
        if all_match:
            result = "PASS"
            reason = None
        else:
            result = "FAIL"
            reason = "PCR_MISMATCH"
        
        latency_ms = (time.time() - start_time) * 1000
        
        return AttestationResult(
            result=result,
            reason=reason,
            timestamp=datetime.now().isoformat(),
            latency_ms=latency_ms,
            pcr_match=pcr_match
        )

attestation_engine = AttestationEngine()


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    print("[STARTUP] FIRM-LOCK Backend starting...")
    print(f"[STARTUP] Hardware available: {HARDWARE_AVAILABLE}")
    yield
    print("[SHUTDOWN] FIRM-LOCK Backend stopping...")

app = FastAPI(
    title="FIRM-LOCK Attestation API",
    description="Backend API for FIRM-LOCK device attestation and fleet management",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    return {
        "name": "FIRM-LOCK Attestation API",
        "version": "1.0.0",
        "hardware_available": HARDWARE_AVAILABLE,
        "status": "operational"
    }


@app.get("/api/devices", response_model=List[DeviceInfo])
async def list_devices():
    """List all registered devices"""
    return list(db.devices.values())


@app.get("/api/devices/{device_id}", response_model=DeviceInfo)
async def get_device(device_id: str):
    """Get device details"""
    if device_id not in db.devices:
        raise HTTPException(status_code=404, detail="Device not found")
    return db.devices[device_id]


@app.post("/api/devices/{device_id}/challenge", response_model=AttestationChallenge)
async def create_challenge(device_id: str):
    """Create attestation challenge for device"""
    if device_id not in db.devices:
        raise HTTPException(status_code=404, detail="Device not found")
    
    challenge = attestation_engine.generate_challenge(device_id)
    
    # Broadcast challenge created event
    await manager.broadcast({
        "type": "challenge_created",
        "device_id": device_id,
        "nonce": challenge.nonce,
        "timestamp": challenge.timestamp
    })
    
    return challenge


@app.post("/api/devices/{device_id}/evidence", response_model=AttestationResult)
async def submit_evidence(device_id: str, evidence: AttestationEvidence):
    """Submit attestation evidence from device"""
    if device_id not in db.devices:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Create challenge object from stored nonce
    challenge = AttestationChallenge(
        nonce=evidence.nonce,
        timestamp=evidence.timestamp,
        device_id=device_id
    )
    
    # Verify evidence
    result = attestation_engine.verify_evidence(evidence, challenge)
    
    # Update device status
    device = db.devices[device_id]
    device.last_attestation = datetime.now().isoformat()
    
    if result.result == "PASS":
        device.status = "healthy"
    elif result.result == "FAIL":
        device.status = "compromised"
    
    # Update PCRs
    device.pcrs = evidence.pcrs
    
    # Log attestation
    db.attestation_logs.insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "type": "Manual",
        "result": result.result,
        "device_id": device_id,
        "latency_ms": round(result.latency_ms, 1)
    })
    
    # Broadcast result
    await manager.broadcast({
        "type": "attestation_complete",
        "device_id": device_id,
        "result": result.result,
        "reason": result.reason,
        "pcr_match": result.pcr_match,
        "latency_ms": round(result.latency_ms, 1)
    })
    
    return result


@app.get("/api/devices/{device_id}/logs")
async def get_device_logs(device_id: str, limit: int = 10):
    """Get attestation logs for device"""
    logs = [log for log in db.attestation_logs if log.get("device_id") == device_id]
    return logs[:limit]


@app.post("/api/devices/{device_id}/recover")
async def recover_device(device_id: str):
    """Trigger golden image recovery for device"""
    if device_id not in db.devices:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device = db.devices[device_id]
    
    # Simulate recovery
    await asyncio.sleep(2)
    
    # Restore golden PCRs
    device.pcrs = db.golden_pcrs[device_id].copy()
    device.status = "healthy"
    device.firmware_version = "v2.1.0-factory"
    
    # Log recovery
    db.attestation_logs.insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "type": "Recovery",
        "result": "PASS",
        "device_id": device_id
    })
    
    # Broadcast recovery event
    await manager.broadcast({
        "type": "device_recovered",
        "device_id": device_id,
        "status": "healthy"
    })
    
    return {
        "result": "SUCCESS",
        "action": "GOLDEN_IMAGE_RESTORED",
        "device_id": device_id,
        "new_firmware": device.firmware_version,
        "status": "healthy"
    }


@app.post("/api/devices/{device_id}/attack")
async def simulate_attack(device_id: str):
    """Simulate firmware attack on device (for demo purposes)"""
    if device_id not in db.devices:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device = db.devices[device_id]
    
    # Modify PCR[1] to simulate compromised application
    compromised_pcr = "0xe5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6"
    device.pcrs[1] = compromised_pcr
    device.status = "compromised"
    
    # Broadcast attack event
    await manager.broadcast({
        "type": "attack_detected",
        "device_id": device_id,
        "pcr_changed": 1,
        "status": "compromised"
    })
    
    return {
        "result": "ATTACK_SIMULATED",
        "device_id": device_id,
        "status": "compromised",
        "modified_pcr": 1,
        "message": "Device compromised - PCR[1] modified"
    }


@app.get("/api/metrics")
async def get_metrics():
    """Get system metrics"""
    return {
        "total_devices": len(db.devices),
        "healthy_devices": sum(1 for d in db.devices.values() if d.status == "healthy"),
        "compromised_devices": sum(1 for d in db.devices.values() if d.status == "compromised"),
        "total_attestations": len(db.attestation_logs),
        "hardware_available": HARDWARE_AVAILABLE
    }


# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    try:
        # Send initial data
        await manager.send_to(websocket, {
            "type": "connected",
            "message": "Connected to FIRM-LOCK backend",
            "hardware_available": HARDWARE_AVAILABLE
        })
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            action = message.get("action")
            
            if action == "ping":
                await manager.send_to(websocket, {"type": "pong"})
                
            elif action == "get_devices":
                await manager.send_to(websocket, {
                    "type": "devices",
                    "data": [d.dict() for d in db.devices.values()]
                })
                
            elif action == "trigger_attestation":
                device_id = message.get("device_id", "FL-2847-AF")
                # Trigger attestation flow
                challenge = attestation_engine.generate_challenge(device_id)
                
                # Simulate device response (in real implementation, device would respond)
                await asyncio.sleep(1)
                
                # Create simulated evidence
                device = db.devices[device_id]
                evidence = AttestationEvidence(
                    device_id=device_id,
                    nonce=challenge.nonce,
                    timestamp=int(time.time()),
                    pcrs=device.pcrs,
                    signature="0x" + secrets.token_hex(64),
                    certificate="0x" + secrets.token_hex(128)
                )
                
                # Verify
                result = attestation_engine.verify_evidence(evidence, challenge)
                
                # Update device
                device.last_attestation = datetime.now().isoformat()
                if result.result == "PASS":
                    device.status = "healthy"
                else:
                    device.status = "compromised"
                
                # Log
                db.attestation_logs.insert(0, {
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "type": "Manual",
                    "result": result.result,
                    "device_id": device_id,
                    "latency_ms": round(result.latency_ms, 1)
                })
                
                # Broadcast
                await manager.broadcast({
                    "type": "attestation_complete",
                    "device_id": device_id,
                    "result": result.result,
                    "reason": result.reason,
                    "pcr_match": result.pcr_match,
                    "latency_ms": round(result.latency_ms, 1)
                })
                
            elif action == "simulate_attack":
                device_id = message.get("device_id", "FL-2847-AF")
                device = db.devices[device_id]
                
                # Modify PCR[1]
                device.pcrs[1] = "0xe5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6"
                device.status = "compromised"
                
                await manager.broadcast({
                    "type": "attack_detected",
                    "device_id": device_id,
                    "pcr_changed": 1,
                    "status": "compromised"
                })
                
            elif action == "trigger_recovery":
                device_id = message.get("device_id", "FL-2847-AF")
                device = db.devices[device_id]
                
                # Restore golden PCRs
                device.pcrs = db.golden_pcrs[device_id].copy()
                device.status = "healthy"
                device.firmware_version = "v2.1.0-factory"
                
                db.attestation_logs.insert(0, {
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "type": "Recovery",
                    "result": "PASS",
                    "device_id": device_id
                })
                
                await manager.broadcast({
                    "type": "device_recovered",
                    "device_id": device_id,
                    "status": "healthy"
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[WEBSOCKET] Error: {e}")
        manager.disconnect(websocket)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
