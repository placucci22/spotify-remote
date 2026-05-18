#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

echo "⚡ Pokemon Price Dashboard"
echo "=========================="

# Backend setup
echo ""
echo "[1/4] Configurando backend Python..."
cd "$BACKEND"
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt

# Frontend setup
echo "[2/4] Instalando dependências do frontend..."
cd "$FRONTEND"
npm install --silent

# Start backend
echo "[3/4] Iniciando backend FastAPI (porta 8000)..."
cd "$BACKEND"
source venv/bin/activate
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
sleep 2

# Start frontend
echo "[4/4] Iniciando frontend React (porta 5173)..."
cd "$FRONTEND"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Dashboard rodando!"
echo "   → Dashboard: http://localhost:5173"
echo "   → API docs:  http://localhost:8000/docs"
echo ""
echo "Pressione Ctrl+C para parar tudo."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Parado.'" EXIT INT TERM
wait
