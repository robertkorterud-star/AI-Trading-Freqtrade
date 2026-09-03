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
import json
from datetime import datetime, timezone
from pathlib import Path

from atlas.adapters.binance import BinanceAdapter
from atlas.core.config import AtlasConfig
from atlas.trading.dry_run_loop import DryRunLoop
from atlas.trading.dry_run_trader import DryRunTrader
from atlas.trading.paper_portfolio_store import PaperPortfolioStore
from atlas.agents import MomentumAgent, TrendAgent, VolumeAgent, VolatilityAgent

SYMBOL = "BTCUSDT"
INTERVAL = "1m"
LIMIT = 100

config = AtlasConfig()
capital_limit = float(config.capital_limit)

print(f"ATLAS capital limit: {capital_limit:.2f} NOK")
print(f"Paper trading:       {config.paper_trading}")
print(f"Trading mode:        {config.trading_mode}")
print()
print(f"Fetching {LIMIT} x {INTERVAL} candles for {SYMBOL}...")
print()

adapter = BinanceAdapter()
portfolio_store = PaperPortfolioStore()
portfolio = portfolio_store.load(initial_cash=capital_limit)
trader = DryRunTrader(portfolio=portfolio, max_position_value=capital_limit)

loop = DryRunLoop(
    agents=[TrendAgent(), MomentumAgent(), VolumeAgent(), VolatilityAgent()],
    trader=trader,
)

result = loop.process_binance(adapter=adapter, symbol=SYMBOL, interval=INTERVAL, limit=LIMIT)

# Persist the complete virtual account between independent dry-run cycles.
portfolio_store.save(portfolio)

# Persist actual virtual position changes for dashboard trade history.
action_value = getattr(result.execution.action, "value", result.execution.action)
if result.execution.executed and result.execution.quantity > 0.0:
    action_map = {"ENTER": "BUY", "REDUCE": "SELL", "EXIT": "SELL"}
    marker_action = action_map.get(str(action_value))
    if marker_action:
        history_path = Path("atlas/dashboard/static/virtual_trades.json")
        history_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            history = json.loads(history_path.read_text())
            if not isinstance(history, list):
                history = []
        except (FileNotFoundError, json.JSONDecodeError):
            history = []

        now = datetime.now(timezone.utc)
        event = {
            "id": now.isoformat() + f"::{result.symbol}::{marker_action}",
            "timestamp": int(now.replace(second=0, microsecond=0).timestamp()),
            "timestamp_iso": now.isoformat(),
            "symbol": result.symbol,
            "action": marker_action,
            "position_action": str(action_value),
            "quantity": result.execution.quantity,
            "price": result.execution.price,
            "confidence": result.decision.confidence,
            "risk_score": result.decision.risk_score,
            "realized_pnl": result.execution.realized_pnl,
            "equity": result.execution.equity,
            "reason": result.execution.reason,
        }
        if not any(item.get("id") == event["id"] for item in history):
            history.append(event)
            history = history[-500:]
            history_path.write_text(json.dumps(history, indent=2) + "\n")
            print(f"Virtual trade persisted: {marker_action} {result.symbol}")

print("========================================")
print(" ATLAS DRY-RUN RESULT")
print("========================================")
print()
print(f"Symbol:              {result.symbol}")
print(f"Price:               {result.price}")
print(f"Intelligence score:  {result.intelligence_score:.4f}")
print(f"Intelligence conf.:  {result.intelligence_confidence:.4f}")
print()

print("Agent observations:")
for observation in result.observations:
    print(f"  {observation.agent:12s} {observation.direction:8s} score={observation.score:.4f} confidence={observation.confidence:.4f}")

print()
print("Algorithm signals:")
for signal in result.algorithm_signals:
    action = getattr(signal.action, "value", signal.action)
    print(f"  {signal.algorithm:24s} {str(action):5s} score={signal.score:.4f} confidence={signal.confidence:.4f}")

print()
print("FINAL ATLAS DECISION")
print("----------------------------------------")
decision_action = getattr(result.decision.action, "value", result.decision.action)
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
print("PERSISTENT PAPER PORTFOLIO")
print("----------------------------------------")
print(f"Cash:         {portfolio.cash}")
print(f"Positions:    {len(portfolio.positions)}")
print(f"Realized PnL: {portfolio.realized_pnl}")
for position in portfolio.positions.values():
    print(f"  {position.symbol}: qty={position.quantity:.8f} avg={position.average_price:.2f}")

print()
print("========================================")
print(" REAL MARKET DATA + VIRTUAL EXECUTION")
print("========================================")
print()
print("No real exchange order was submitted.")
print()
PY
