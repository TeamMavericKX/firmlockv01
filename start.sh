#!/bin/bash
# =============================================================================
# FIRM-LOCK Startup Script
# Starts both backend and frontend for demo
# =============================================================================

set -e

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                    FIRM-LOCK DEMO STARTER                            ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check dependencies
echo -e "${BLUE}[CHECK]${NC} Checking dependencies..."

if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install Python 3.9+"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "ERROR: npm not found. Please install Node.js 18+"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Dependencies found"
echo ""

# Setup backend if needed
if [ ! -d "backend/venv" ]; then
    echo -e "${BLUE}[SETUP]${NC} Setting up backend..."
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
    echo -e "${GREEN}[OK]${NC} Backend setup complete"
fi

# Setup frontend if needed
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}[SETUP]${NC} Installing frontend dependencies..."
    npm install
    echo -e "${GREEN}[OK]${NC} Frontend setup complete"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                        STARTING SERVICES                             ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Start backend in background
echo -e "${BLUE}[START]${NC} Starting backend on http://localhost:8000"
cd backend
source venv/bin/activate
python main.py &
BACKEND_PID=$!
cd ..

echo -e "${GREEN}[OK]${NC} Backend started (PID: $BACKEND_PID)"
echo ""

# Wait for backend to be ready
echo -e "${BLUE}[WAIT]${NC} Waiting for backend to be ready..."
sleep 3

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "ERROR: Backend failed to start"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Backend is ready"
echo ""

# Start frontend
echo -e "${BLUE}[START]${NC} Starting frontend on http://localhost:5173"
echo ""

# Trap Ctrl+C to kill backend
trap "echo ''; echo 'Shutting down...'; kill $BACKEND_PID 2>/dev/null; exit 0" INT

npm run dev
