#!/bin/bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$PROJECT_DIR"

echo "========================================"
echo " ATLAS — REAL MARKET DATA DRY RUN"
echo "========================================"
echo
echo "Project: $PROJECT_DIR"
echo

if [ ! -d ".venv" ]; then
    echo "ERROR: .venv not found."
    exit 1
fi

source .venv/bin/activate

echo "Python:"
python --version
echo

echo "Running ATLAS dry-run smoke test..."
echo "Market data: Binance public REST API"
echo "Execution:    VIRTUAL ONLY"
echo "Real orders:  DISABLED"
echo

python - <<'PY'
from atlas.adapters.binance import BinanceAdapter
from atlas.trading.dry_run_loop import DryRunLoop
from atlas.agents import (
    MomentumAgent,
    TrendAgent,
    VolumeAgent,
    VolatilityAgent,
)

SYMBOL = "BTCUSDT"
INTERVAL = "1m"
LIMIT = 100

print(f"Fetching {LIMIT} x {INTERVAL} candles for {SYMBOL}...")
print()

adapter = BinanceAdapter()

loop = DryRunLoop(
    agents=[
        TrendAgent(),
        MomentumAgent(),
        VolumeAgent(),
        VolatilityAgent(),
    ]
)

result = loop.process_binance(
    adapter=adapter,
    symbol=SYMBOL,
    interval=INTERVAL,
    limit=LIMIT,
)

print("========================================")
print(" ATLAS DRY-RUN RESULT")
print("========================================")
print()
print(f"Symbol:              {result.symbol}")
print(f"Price:               {result.price}")
print(
    f"Intelligence score:  "
    f"{result.intelligence_score:.4f}"
)
print(
    f"Intelligence conf.:  "
    f"{result.intelligence_confidence:.4f}"
)
print()

print("Agent observations:")
for observation in result.observations:
    print(
        f"  {observation.agent:12s} "
        f"{observation.direction:8s} "
        f"score={observation.score:.4f} "
        f"confidence={observation.confidence:.4f}"
    )

print()
print("Algorithm signals:")
for signal in result.algorithm_signals:
    action = getattr(signal.action, "value", signal.action)

    print(
        f"  {signal.algorithm:24s} "
        f"{str(action):5s} "
        f"score={signal.score:.4f} "
        f"confidence={signal.confidence:.4f}"
    )

print()
print("FINAL ATLAS DECISION")
print("----------------------------------------")

decision_action = getattr(
    result.decision.action,
    "value",
    result.decision.action,
)

print(f"Action:       {decision_action}")
print(f"Score:        {result.decision.score:.4f}")
print(f"Confidence:   {result.decision.confidence:.4f}")
print(f"Risk score:   {result.decision.risk_score:.4f}")
print(f"Reason:       {result.decision.reason}")

print()
print("DRY-RUN EXECUTION")
print("----------------------------------------")
print(f"Action:       {result.execution.action}")
print(f"Quantity:     {result.execution.quantity}")
print(f"Price:        {result.execution.price}")
print(f"Target pos.:  {result.execution.target_position}")
print(f"Equity:       {result.execution.equity}")
print(f"Realized PnL: {result.execution.realized_pnl}")
print(f"Executed:     {result.execution.executed}")
print(f"Reason:       {result.execution.reason}")

print()
print("========================================")
print(" REAL MARKET DATA + VIRTUAL EXECUTION")
print("========================================")
print()
print("No real exchange order was submitted.")
print()
PY
