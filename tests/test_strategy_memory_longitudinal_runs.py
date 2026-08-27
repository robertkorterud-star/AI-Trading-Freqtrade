from datetime import datetime, timedelta, timezone

from atlas.trading.strategy_memory import StrategyMemoryRecord
from atlas.trading.strategy_memory_longitudinal_analyzer import (
    StrategyMemoryLongitudinalAnalyzer,
)


def _record(
    *,
    total_return=20.0,
    days_ago=10,
):
    return StrategyMemoryRecord(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
        trade_count=20,
        winning_trades=15,
        losing_trades=5,
        win_rate_percent=75.0,
        average_trade_return_percent=2.0,
        total_return_percent=total_return,
        evidence_strength="STRONG",
        robust_winner=True,
        updated_at=(
            datetime.now(timezone.utc)
            - timedelta(days=days_ago)
        ),
    )


def test_same_research_run_does_not_count_twice():
    analyzer = StrategyMemoryLongitudinalAnalyzer()

    history = (
        _record(total_return=20.0, days_ago=30),
        _record(total_return=20.0, days_ago=29),
        _record(total_return=25.0, days_ago=10),
    )

    result = analyzer.analyze(history)

    assert result.observation_count == 3


def test_more_observations_still_increase_confidence():
    analyzer = StrategyMemoryLongitudinalAnalyzer()

    short_history = (
        _record(total_return=20.0, days_ago=20),
        _record(total_return=22.0, days_ago=10),
    )

    long_history = (
        _record(total_return=20.0, days_ago=40),
        _record(total_return=21.0, days_ago=30),
        _record(total_return=22.0, days_ago=20),
        _record(total_return=23.0, days_ago=10),
    )

    short_result = analyzer.analyze(short_history)
    long_result = analyzer.analyze(long_history)

    assert long_result.confidence >= short_result.confidence
