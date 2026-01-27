# 🔧 FIRM-LOCK Hardware Setup Guide

> **Complete guide for connecting real STM32 + ATECC608A hardware**

---

## 📋 Required Components

### Minimum Setup (For Demo)

| Component | Part Number | Supplier | Cost |
|:----------|:------------|:---------|:-----|
| STM32 Nucleo Board | NUCLEO-U585AI-Q | Mouser/Digi-Key | ~$15 |
| ATECC608A Breakout | Adafruit #4314 | Adafruit | ~$8 |
| USB Cable | Micro-USB | Any | ~$3 |
| Jumper Wires | M-M, 10pcs | Any | ~$2 |
| **Total** | | | **~$28** |

### Full Setup (With LoRa)

| Component | Part Number | Supplier | Cost |
|:----------|:------------|:---------|:-----|
| STM32 Nucleo Board | NUCLEO-U585AI-Q | Mouser/Digi-Key | ~$15 |
| ATECC608A Breakout | Adafruit #4314 | Adafruit | ~$8 |
| RFM95W LoRa Module | Adafruit #3072 | Adafruit | ~$20 |
| Antenna | 915MHz Dipole | Adafruit | ~$5 |
| Breadboard | Half-size | Any | ~$5 |
| Jumper Wires | Assorted | Any | ~$5 |
| **Total** | | | **~$58** |

---

## 🔌 Wiring Diagram

### STM32 Nucleo-U585 to ATECC608A (I2C)

```
┌─────────────────────────────────────────────────────────────────┐
│                    WIRING DIAGRAM                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   STM32 Nucleo-U585         ATECC608A Breakout                  │
│   ─────────────────         ──────────────────                  │
│                                                                 │
│   3.3V (CN8 Pin 7)  ───────  VCC (Red)                          │
│   GND (CN8 Pin 5)   ───────  GND (Black)                        │
│   PB7 (I2C1_SDA)    ───────  SDA (Blue)                         │
│   PB6 (I2C1_SCL)    ───────  SCL (Yellow)                       │
│                                                                 │
│   Note: ATECC608A I2C address is 0x60 (96 decimal)              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Pin Mapping

| STM32 Pin | Function | ATECC608A Pin |
|:----------|:---------|:--------------|
| 3.3V | Power | VCC |
| GND | Ground | GND |
| PB7 | I2C SDA | SDA |
| PB6 | I2C SCL | SCL |

### STM32 Nucleo-U585 to RFM95W LoRa (SPI) - Optional

```
STM32 Nucleo-U585         RFM95W LoRa Module
────────────────────────────────────────────
3.3V              ─────── VCC
GND               ─────── GND
PA5 (SPI1_SCK)    ─────── SCK
PA6 (SPI1_MISO)   ─────── MISO
PA7 (SPI1_MOSI)   ─────── MOSI
PA4 (GPIO)        ─────── NSS
PA0 (GPIO)        ─────── RST
PA1 (GPIO)        ─────── DIO0
```

---

## 🔨 Assembly Instructions

### Step 1: Prepare the STM32 Board

1. **Remove JP5 jumper** on Nucleo board (disables ST-Link power)
2. **Connect USB cable** to CN1 (ST-Link USB)
3. **Verify LEDs**: LD1 (COM) should blink, LD3 (PWR) should be ON

### Step 2: Connect ATECC608A

1. **Place ATECC608A breakout** on breadboard
2. **Connect power**: 3.3V → VCC, GND → GND
3. **Connect I2C**: PB7 → SDA, PB6 → SCL
4. **Add pull-up resistors** (if not on breakout): 4.7kΩ from SDA to 3.3V, SCL to 3.3V

### Step 3: Verify Connections

```bash
# Check I2C devices
sudo apt-get install i2c-tools
sudo i2cdetect -y 1

# Should show device at 0x60:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 00:                         -- -- -- -- -- -- -- --
# 10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 60: 60 -- -- -- -- -- -- -- -- -- -- -- -- -- -- --  <-- ATECC608A!
# 70: -- -- -- -- -- -- -- --
```

---

## 💻 Software Setup

### 1. Install STM32 Firmware

The STM32 firmware handles:
- Secure boot with signature verification
- Measured boot with PCR extension
- Attestation protocol
- Hardware crypto via ATECC608A

**Option A: Pre-built Binary**
```bash
# Download firmware from releases
wget https://github.com/yourteam/firmlock-firmware/releases/download/v1.0.0/firmlock-firmware.bin

# Flash using STM32CubeProgrammer or openocd
openocd -f interface/stlink.cfg -f target/stm32u5x.cfg \
  -c "program firmlock-firmware.bin 0x08000000 verify reset exit"
```

**Option B: Build from Source**
```bash
# Clone firmware repository
git clone https://github.com/yourteam/firmlock-firmware.git
cd firmlock-firmware

# Build with STM32CubeIDE or Makefile
make

# Flash to device
make flash
```

### 2. Test Hardware Connection

```bash
# Navigate to backend
cd firm-lock/backend
source venv/bin/activate

# Test hardware interface
python -c "
from hardware.device_interface import DeviceInterface
device = DeviceInterface()
if device.connect():
    print('✓ Device connected')
    info = device.get_device_info()
    print(f'✓ Device ID: {info[\"device_id\"]}')
    pcrs = device.get_pcrs()
    print(f'✓ PCRs: {len(pcrs)} registers')
    device.disconnect()
else:
    print('✗ Failed to connect')
"
```

### 3. Run Full System

```bash
# Terminal 1: Start backend
cd firm-lock/backend
source venv/bin/activate
python main.py

# Terminal 2: Start frontend
cd firm-lock
npm run dev

# Browser: Open http://localhost:5173
```

---

## 🔍 Troubleshooting

### Device Not Detected

**Symptom**: Backend shows "No device found"

**Solutions**:
1. Check USB cable (try different cable)
2. Verify STM32 is powered (LD3 LED)
3. Check serial port permissions:
   ```bash
   sudo usermod -aG dialout $USER
   # Log out and back in
   ```
4. List available ports:
   ```bash
   python -m serial.tools.list_ports
   ```

### I2C Communication Fails

**Symptom**: ATECC608A not responding

**Solutions**:
1. Verify wiring (SDA ↔ SDA, SCL ↔ SCL)
2. Check pull-up resistors (4.7kΩ)
3. Verify I2C address:
   ```bash
   sudo i2cdetect -y 1
   ```
4. Try different I2C pins on STM32

### Attestation Fails

**Symptom**: PCRs don't match or signature invalid

**Solutions**:
1. Check firmware version matches expected
2. Verify device was provisioned (keys generated)
3. Check secure element is responding
4. Review terminal output for errors

---

## 📊 Expected Behavior

### Normal Boot Sequence

```
[BOOT] FIRM-LOCK v2.1.0 starting...
[BOOT] Initializing hardware...
[BOOT] ATECC608A detected at 0x60
[BOOT] Reading device certificate...
[BOOT] Device ID: FL-2847-AF
[BOOT] Measuring bootloader...
[BOOT] PCR[0] = 0x7a8b9c...
[BOOT] Verifying application signature...
[BOOT] Signature valid ✓
[BOOT] Measuring application...
[BOOT] PCR[1] = 0xa1b2c3d...
[BOOT] Boot complete. System ready.
[MAIN] Attestation agent started.
```

### Attestation Flow

```
[ATTEST] Challenge received: 0x8f3a9e2d...
[ATTEST] Collecting PCR values...
[ATTEST] PCR[0] = 0x7a8b9c...
[ATTEST] PCR[1] = 0xa1b2c3d...
[ATTEST] PCR[2] = 0xd4e5f6a...
[ATTEST] PCR[3] = 0x9a8b7c6...
[ATTEST] Signing evidence with ATECC608A...
[ATTEST] Signature complete (52ms)
[ATTEST] Sending evidence to verifier...
[ATTEST] Result: PASS ✓
```

---

## 🎯 Demo Checklist

Before your hackathon demo:

- [ ] STM32 board programmed with firmware
- [ ] ATECC608A connected and responding
- [ ] Backend connects to device successfully
- [ ] Dashboard shows "Hardware" badge
- [ ] Attestation completes in <2 seconds
- [ ] Attack simulation works
- [ ] Recovery process works
- [ ] Backup device ready (if possible)
- [ ] All cables organized and labeled

---

## 🔐 Security Notes

### Device Provisioning

Each device must be provisioned before use:

1. **Generate device key pair** in ATECC608A
2. **Create device certificate** signed by root CA
3. **Lock configuration zone** to prevent modification
4. **Record device ID** in verifier database

```bash
# Provision script (run once per device)
python scripts/provision_device.py --device-id FL-2847-AF
```

### Production Considerations

- Use **unique device keys** per device (never shared)
- Store **root CA keys** in HSM
- Implement **secure key ceremony** for provisioning
- Enable **tamper detection** on production boards

---

## 📚 Resources

### Datasheets

- [STM32U585 Reference Manual](https://www.st.com/resource/en/reference_manual/rm0456-stm32u575585-armbased-32bit-mcus-stmicroelectronics.pdf)
- [ATECC608A Datasheet](https://ww1.microchip.com/downloads/en/DeviceDoc/ATECC608A-CryptoAuthentication-Device-Summary-Data-Sheet-DS40001977B.pdf)
- [RFM95W Datasheet](https://www.hoperf.com/data/upload/portal/20190801/RFM95-96-97-98W.pdf)

### Tools

- [STM32CubeIDE](https://www.st.com/en/development-tools/stm32cubeide.html) - IDE for STM32
- [STM32CubeProgrammer](https://www.st.com/en/development-tools/stm32cubeprog.html) - Flash programming
- [OpenOCD](https://openocd.org/) - Open source debugger

### Libraries

- [CryptoAuthLib](https://github.com/MicrochipTech/cryptoauthlib) - ATECC608A driver
- [MCUboot](https://www.mcuboot.com/) - Secure bootloader

---

**Questions?** Open an issue on GitHub or email [support@firmlock.io](mailto:support@firmlock.io)

---

*Hardware Setup Guide v1.0*
