#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
  echo "ERROR: .venv not found."
  exit 1
fi

source .venv/bin/activate

INTERVAL_SECONDS="${ATLAS_RUNTIME_INTERVAL_SECONDS:-30}"

echo "ATLAS Runtime: continuous canonical trading cycle"
echo "Cycle interval: ${INTERVAL_SECONDS}s"
echo "Mode: configured by AtlasConfig"

exec python -c "from atlas.core.runtime_loop import run; run(interval_seconds=float('${INTERVAL_SECONDS}'))"
