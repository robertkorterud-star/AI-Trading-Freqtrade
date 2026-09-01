#!/bin/bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"
if [ ! -d ".venv" ]; then
  echo "ERROR: .venv not found."
  exit 1
fi
source .venv/bin/activate
python -m atlas.dashboard.server
