#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
  echo "ERROR: .venv not found."
  exit 1
fi

source .venv/bin/activate

echo "ATLAS Dashboard: http://127.0.0.1:8080"
echo "Mode: ADVISOR / DRY-RUN — NO REAL ORDERS"
echo "Server: FastAPI + Uvicorn"

exec uvicorn atlas.dashboard.app:app \
  --host 127.0.0.1 \
  --port 8080
