"""Run one ATLAS dry-run cycle against Binance public market data.

This entrypoint is deliberately read-only against Binance. It fetches public
market data only and sends the resulting decision to ATLAS's paper portfolio.
No Binance order endpoint, credentials, or live execution adapter is used.
"""

from __future__ import annotations

import argparse
import json

from atlas.adapters.binance import BinanceAdapter
from atlas.trading.dry_run_loop import DryRunLoop


def run_dry_run(
    symbol: str = "BTCUSDT",
    interval: str = "1m",
    limit: int = 100,
):
    """Fetch public Binance data and process exactly one simulated cycle."""
    if limit <= 0:
        raise ValueError("limit must be greater than zero")

    adapter = BinanceAdapter()
    loop = DryRunLoop(agents=[])
    return loop.process_binance(
        adapter,
        symbol=symbol,
        interval=interval,
        limit=limit,
    )


def _summary(result) -> dict:
    """Convert the dry-run result into a compact CLI-safe summary."""
    engine = getattr(result, "decision", None)
    return {
        "mode": "DRY_RUN",
        "symbol": result.symbol,
        "price": result.price,
        "decision": getattr(engine.action, "value", str(engine.action)),
        "confidence": engine.confidence,
        "risk_score": engine.risk_score,
        "expected_return": result.expected_return,
        "paper_execution": {
            "action": result.execution.action.value,
            "quantity": result.execution.quantity,
            "equity": result.execution.equity,
            "executed": result.execution.executed,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one safe ATLAS Binance public-data dry-run cycle."
    )
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="1m")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    result = run_dry_run(
        symbol=args.symbol,
        interval=args.interval,
        limit=args.limit,
    )
    print(json.dumps(_summary(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
