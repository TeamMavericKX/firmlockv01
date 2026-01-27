# 🚀 FIRM-LOCK Quick Start Guide

> **Get the full-stack demo running in 5 minutes**

---

## ✅ Prerequisites

- **Python 3.9+**
- **Node.js 18+**
- **Git**

---

## 🎬 Option 1: One-Command Start (Recommended)

```bash
cd /mnt/okcomputer/output/app
./start.sh
```

This will:
1. Set up Python virtual environment
2. Install backend dependencies
3. Install frontend dependencies
4. Start backend on `http://localhost:8000`
5. Start frontend on `http://localhost:5173`

Then open **http://localhost:5173** in your browser!

---

## 🛠️ Option 2: Manual Setup

### Step 1: Start Backend

```bash
cd /mnt/okcomputer/output/app/backend

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start server
python main.py
```

Backend running at: **http://localhost:8000**

### Step 2: Start Frontend

```bash
# In a new terminal
cd /mnt/okcomputer/output/app

# Install dependencies (if not done)
npm install

# Start dev server
npm run dev
```

Frontend running at: **http://localhost:5173**

---

## 🎮 Demo Flow

### 1. Normal Operation

1. Open **http://localhost:5173**
2. See device status: **🟢 HEALTHY**
3. See all 4 PCRs matching ✓

### 2. Trigger Attestation

1. Click **"Trigger Attestation"**
2. Watch progress bar
3. See result in ~1.2 seconds
4. Check terminal output

### 3. Simulate Attack

1. Click **"Simulate Attack"**
2. Watch terminal for attack steps
3. See device status change to **🔴 COMPROMISED**
4. See PCR[1] show mismatch ✗

### 4. Trigger Recovery

1. Click **"Trigger Recovery"**
2. Watch recovery process
3. See device restored to **🟢 HEALTHY**
4. All PCRs match again ✓

---

## 🔌 Connect Real Hardware (Optional)

### Required Hardware

| Component | Cost | Where to Buy |
|:----------|:-----|:-------------|
| STM32 Nucleo-U585 | ~$15 | Mouser, Digi-Key |
| ATECC608A Breakout | ~$8 | Adafruit |
| USB Cable | ~$3 | Any |

### Wiring

```
STM32 Nucleo-U585    ATECC608A
──────────────────────────────
3.3V    ───────────  VCC
GND     ───────────  GND
PB7     ───────────  SDA (I2C)
PB6     ───────────  SCL (I2C)
```

### Flash Firmware

```bash
# Download firmware from releases
wget https://github.com/yourteam/firmlock-firmware/releases/download/v1.0.0/firmware.bin

# Flash using openocd
openocd -f interface/stlink.cfg -f target/stm32u5x.cfg \
  -c "program firmware.bin 0x08000000 verify reset exit"
```

### Test Connection

```bash
cd backend
source venv/bin/activate
python -c "
from hardware.device_interface import DeviceInterface
d = DeviceInterface()
print('Connected!' if d.connect() else 'Failed')
"
```

---

## 📁 Project Structure

```
app/
├── backend/
│   ├── main.py                 # FastAPI backend
│   ├── requirements.txt        # Python deps
│   └── hardware/
│       └── device_interface.py # STM32/ATECC608A interface
├── src/
│   ├── App.tsx                 # React dashboard
│   └── App.css                 # Styles
├── dist/                       # Built frontend
├── start.sh                    # One-command starter
├── README.md                   # Full documentation
├── HARDWARE_SETUP.md           # Hardware guide
└── QUICKSTART.md               # This file
```

---

## 🔗 Key URLs

| Service | URL | Description |
|:--------|:----|:------------|
| Frontend | http://localhost:5173 | Dashboard UI |
| Backend API | http://localhost:8000 | REST API |
| API Docs | http://localhost:8000/docs | Swagger UI |
| WebSocket | ws://localhost:8000/ws | Real-time updates |

---

## 🐛 Troubleshooting

### Backend won't start

```bash
# Check Python version
python3 --version  # Should be 3.9+

# Check port 8000 is free
lsof -i :8000

# Try different port
python main.py --port 8001
```

### Frontend won't start

```bash
# Check Node version
node --version  # Should be 18+

# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### WebSocket not connecting

1. Make sure backend is running
2. Check firewall settings
3. Try refreshing the page

---

## 🎯 Next Steps

1. **Customize the demo**: Edit `src/App.tsx`
2. **Add more devices**: Edit `backend/main.py`
3. **Connect real hardware**: Follow `HARDWARE_SETUP.md`
4. **Deploy to cloud**: Build with `npm run build`

---

## 📞 Support

- **GitHub Issues**: [github.com/yourteam/firm-lock](https://github.com/yourteam/firm-lock)
- **Email**: support@firmlock.io

---

**Trust Your Edge. Verify Every Boot.** 🔒
