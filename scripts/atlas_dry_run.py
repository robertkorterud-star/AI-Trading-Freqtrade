"""Run ATLAS dry-run cycles against Binance public market data.

This entrypoint is deliberately read-only against Binance. It fetches public
market data only and sends the resulting decisions to ATLAS's paper portfolio.
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
    if not symbol.strip():
        raise ValueError("symbol must not be empty")
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


def run_dry_runs(
    symbols: list[str],
    interval: str = "1m",
    limit: int = 100,
) -> list:
    """Run independent dry-run cycles for a list of symbols."""
    if not symbols:
        raise ValueError("at least one symbol is required")
    return [
        run_dry_run(symbol=symbol.strip().upper(), interval=interval, limit=limit)
        for symbol in symbols
    ]


def _summary(result) -> dict:
    """Convert one dry-run result into a diagnostic, CLI-safe summary."""
    compatibility_decision = getattr(result, "decision", None)
    engine = getattr(result, "canonical_decision", None) or compatibility_decision
    risk_assessment = getattr(engine, "risk_assessment", None)
    portfolio_assessment = getattr(engine, "portfolio_assessment", None)

    return {
        "mode": "DRY_RUN",
        "symbol": result.symbol,
        "price": result.price,
        "decision": getattr(engine.action, "value", str(engine.action)),
        "confidence": engine.confidence,
        "evidence": getattr(engine, "evidence", None),
        "dominant_action": getattr(
            engine.dominant_action, "value", str(engine.dominant_action)
        ),
        "dominant_weight": getattr(engine, "dominant_weight", None),
        "decision_margin": getattr(engine, "decision_margin", None),
        "robustness": getattr(engine, "robustness", None),
        "robustness_level": getattr(engine, "robustness_level", None),
        "ensemble": {
            "action": getattr(
                engine.ensemble_action, "value", str(engine.ensemble_action)
            ),
            "confidence": getattr(engine, "ensemble_confidence", None),
        },
        "intelligence": {
            "score": result.intelligence_score,
            "confidence": result.intelligence_confidence,
        },
        "algorithm_signals": [
            {
                "algorithm": signal.algorithm,
                "action": getattr(signal.action, "value", str(signal.action)),
                "score": signal.score,
                "confidence": signal.confidence,
                "timeframe": signal.timeframe,
                "reasoning": list(signal.reasoning),
            }
            for signal in result.algorithm_signals
        ],
        "opposing_analysts": list(getattr(engine, "opposing_analysts", [])),
        "reasoning": list(getattr(engine, "reasoning", [])),
        "risk": (
            {
                "allowed": risk_assessment.allowed,
                "risk_level": risk_assessment.risk_level,
                "position_size": risk_assessment.position_size,
                "position_value": risk_assessment.position_value,
                "reasons": list(risk_assessment.reasons),
            }
            if risk_assessment is not None
            else None
        ),
        "portfolio": (
            {
                "allowed": portfolio_assessment.allowed,
                "requested_value": portfolio_assessment.requested_value,
                "approved_value": portfolio_assessment.approved_value,
                "reasons": list(portfolio_assessment.reasons),
            }
            if portfolio_assessment is not None
            else None
        ),
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
        description="Run safe ATLAS Binance public-data dry-run cycle(s)."
    )
    parser.add_argument(
        "--symbol",
        action="append",
        dest="symbols",
        help="Symbol to test; may be supplied multiple times.",
    )
    parser.add_argument("--interval", default="1m")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    symbols = args.symbols or ["BTCUSDT"]
    results = run_dry_runs(symbols, interval=args.interval, limit=args.limit)
    summaries = [_summary(result) for result in results]
    print(
        json.dumps(
            summaries[0] if len(summaries) == 1 else summaries,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
