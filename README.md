# 🔒 FIRM-LOCK: Full-Stack Attestation System

> **Working demo of military-grade firmware integrity for edge IoT**

---

## 🎯 What This Is

This is a **complete, working implementation** of the FIRM-LOCK attestation system:

- ✅ **Backend**: FastAPI with WebSocket for real-time updates
- ✅ **Frontend**: React dashboard with professional UI
- ✅ **Hardware Interface**: Python module for STM32 + ATECC608A communication
- ✅ **Simulation Mode**: Works without hardware for demos

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FIRM-LOCK SYSTEM                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐      WebSocket       ┌─────────────────────────────┐ │
│  │   React      │◀────────────────────▶│      FastAPI Backend        │ │
│  │  Dashboard   │      HTTP API        │                             │ │
│  │              │                      │  • Attestation Engine         │ │
│  │  • Real-time │                      │  • Device Registry            │ │
│  │  • PCR viz   │                      │  • Challenge/Response         │ │
│  │  • Controls  │                      │  • WebSocket Manager          │ │
│  └──────────────┘                      └──────────────┬──────────────┘ │
│                                                       │                 │
│                                                       │ Serial/USB      │
│                                                       ▼                 │
│                                         ┌─────────────────────────────┐│
│                                         │   Hardware Interface        ││
│                                         │                             ││
│                                         │  • STM32 (Cortex-M33)       ││
│                                         │  • ATECC608A Secure Element ││
│                                         │  • LoRa/BLE/USB Comms       ││
│                                         └─────────────────────────────┘│
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- (Optional) STM32 Nucleo board + ATECC608A for hardware mode

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/yourteam/firm-lock.git
cd firm-lock

# Setup backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup frontend (in another terminal)
cd ../
npm install
```

### 2. Start the Backend

```bash
cd backend
source venv/bin/activate
python main.py
```

Backend will start at `http://localhost:8000`

### 3. Start the Frontend

```bash
# In project root
npm run dev
```

Frontend will start at `http://localhost:5173`

### 4. Open Dashboard

Navigate to `http://localhost:5173` in your browser.

---

## 🎮 Demo Flow

### Without Hardware (Simulation Mode)

1. **Open Dashboard** → See device status as "HEALTHY"
2. **Click "Trigger Attestation"** → Watch real-time verification
3. **Click "Simulate Attack"** → See PCR mismatch detection
4. **Click "Trigger Recovery"** → Watch automatic restoration

### With Hardware (Real Device)

1. **Connect STM32** via USB
2. **Backend auto-detects** device
3. **Dashboard shows** "Hardware" badge
4. **All operations** communicate with real device

---

## 📁 Project Structure

```
firm-lock/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── requirements.txt        # Python dependencies
│   └── hardware/
│       ├── __init__.py
│       └── device_interface.py # STM32/ATECC608A interface
├── src/
│   ├── App.tsx                 # Main React application
│   ├── App.css                 # Custom styles
│   └── ...                     # React components
├── index.html                  # HTML entry point
├── package.json                # Node dependencies
├── vite.config.ts              # Vite configuration
└── README.md                   # This file
```

---

## 🔌 Hardware Setup (Optional)

### Required Components

| Component | Part Number | Cost |
|:----------|:------------|:-----|
| MCU Dev Board | STM32 Nucleo-U585 | ~$15 |
| Secure Element | ATECC608A Breakout | ~$8 |
| LoRa Module | RFM95W Breakout | ~$20 |

### Wiring

```
STM32 Nucleo-U585         ATECC608A
────────────────────────────────────
3.3V      ─────────────── VCC
GND       ─────────────── GND
PB7 (I2C) ─────────────── SDA
PB6 (I2C) ─────────────── SCL

STM32 Nucleo-U585         RFM95W
────────────────────────────────────
3.3V      ─────────────── VCC
GND       ─────────────── GND
PA5 (SPI) ─────────────── SCK
PA6 (SPI) ─────────────── MISO
PA7 (SPI) ─────────────── MOSI
PA4 (GPIO) ─────────────── NSS
```

### Firmware

The STM32 firmware is in a separate repository:
[github.com/yourteam/firmlock-firmware](https://github.com/yourteam/firmlock-firmware)

---

## 🔧 API Endpoints

### REST API

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/api/devices` | GET | List all devices |
| `/api/devices/{id}` | GET | Get device details |
| `/api/devices/{id}/challenge` | POST | Create attestation challenge |
| `/api/devices/{id}/evidence` | POST | Submit attestation evidence |
| `/api/devices/{id}/recover` | POST | Trigger recovery |
| `/api/devices/{id}/attack` | POST | Simulate attack (demo) |
| `/api/metrics` | GET | System metrics |

### WebSocket

Connect to `ws://localhost:8000/ws`

**Client → Server Messages:**
```json
{ "action": "ping" }
{ "action": "get_devices" }
{ "action": "trigger_attestation", "device_id": "FL-2847-AF" }
{ "action": "simulate_attack", "device_id": "FL-2847-AF" }
{ "action": "trigger_recovery", "device_id": "FL-2847-AF" }
```

**Server → Client Messages:**
```json
{ "type": "connected", "hardware_available": true }
{ "type": "attestation_complete", "result": "PASS", "latency_ms": 1.2 }
{ "type": "attack_detected", "device_id": "FL-2847-AF" }
{ "type": "device_recovered", "device_id": "FL-2847-AF" }
```

---

## 🧪 Testing

### Backend Tests

```bash
cd backend
pytest
```

### Frontend Tests

```bash
npm test
```

### Manual Testing

1. Start backend and frontend
2. Open browser DevTools → Network → WS
3. Watch WebSocket messages
4. Click buttons, verify responses

---

## 📦 Building for Production

### Build Frontend

```bash
npm run build
```

Output in `dist/` folder.

### Deploy Backend

```bash
cd backend
# Using Docker
docker build -t firmlock-backend .
docker run -p 8000:8000 firmlock-backend

# Or using systemd
systemctl enable firmlock-backend
systemctl start firmlock-backend
```

---

## 🎓 Learning Resources

### Understanding the Code

1. **Start with `backend/main.py`** - Core attestation logic
2. **Read `hardware/device_interface.py`** - Hardware communication
3. **Explore `src/App.tsx`** - Dashboard UI

### Key Concepts

- **PCR (Platform Configuration Register)**: Cryptographic hash of firmware
- **Measured Boot**: Hashing each boot stage
- **Challenge-Response**: Verifier sends nonce, device signs evidence
- **Golden Image**: Factory-trusted firmware for recovery

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file

---

## 🙏 Acknowledgments

- MCUboot project for secure bootloader
- Microchip for ATECC608A secure element
- STMicroelectronics for STM32 platform

---

## 📧 Contact

- Team: [yourteam@firmlock.io](mailto:yourteam@firmlock.io)
- Twitter: [@firmlock](https://twitter.com/firmlock)
- GitHub: [github.com/yourteam/firm-lock](https://github.com/yourteam/firm-lock)

---

**Trust Your Edge. Verify Every Boot.** 🔒
