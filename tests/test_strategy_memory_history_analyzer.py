from datetime import datetime, timedelta, timezone

from atlas.trading.strategy_memory import StrategyMemoryRecord
from atlas.trading.strategy_memory_history_analyzer import (
    StrategyMemoryHistoryAnalyzer,
)


def _record(
    *,
    trade_count=20,
    win_rate=75.0,
    average_return=2.0,
    total_return=40.0,
    robust_winner=True,
    days_ago=0,
):
    return StrategyMemoryRecord(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
        trade_count=trade_count,
        winning_trades=15,
        losing_trades=5,
        win_rate_percent=win_rate,
        average_trade_return_percent=average_return,
        total_return_percent=total_return,
        evidence_strength="STRONG",
        robust_winner=robust_winner,
        updated_at=(
            datetime.now(timezone.utc)
            - timedelta(days=days_ago)
        ),
    )


def test_empty_history_is_insufficient():
    analyzer = StrategyMemoryHistoryAnalyzer()

    result = analyzer.analyze(())

    assert result.observation_count == 0
    assert result.classification == "INSUFFICIENT_DATA"
    assert result.consistency_score == 0.0


def test_single_observation_is_insufficient():
    analyzer = StrategyMemoryHistoryAnalyzer()

    result = analyzer.analyze(
        (_record(),)
    )

    assert result.observation_count == 1
    assert result.classification == "INSUFFICIENT_DATA"


def test_consistent_positive_history():
    analyzer = StrategyMemoryHistoryAnalyzer()

    history = (
        _record(total_return=20.0, days_ago=30),
        _record(total_return=25.0, days_ago=20),
        _record(total_return=30.0, days_ago=10),
    )

    result = analyzer.analyze(history)

    assert result.observation_count == 3
    assert result.average_return_percent == 25.0
    assert result.best_return_percent == 30.0
    assert result.worst_return_percent == 20.0
    assert result.positive_periods == 3
    assert result.positive_period_ratio == 1.0
    assert result.robust_winner_periods == 3
    assert result.classification == "CONSISTENT"
    assert result.consistency_score > 0.0


def test_mixed_history_is_not_consistent():
    analyzer = StrategyMemoryHistoryAnalyzer()

    history = (
        _record(total_return=20.0, days_ago=30),
        _record(total_return=-15.0, days_ago=20),
        _record(total_return=10.0, days_ago=10),
    )

    result = analyzer.analyze(history)

    assert result.observation_count == 3
    assert result.positive_periods == 2
    assert result.positive_period_ratio == 2 / 3
    assert result.classification == "MIXED"


def test_unstable_history_has_large_variation():
    analyzer = StrategyMemoryHistoryAnalyzer()

    history = (
        _record(total_return=50.0, days_ago=30),
        _record(total_return=-40.0, days_ago=20),
        _record(total_return=60.0, days_ago=10),
    )

    result = analyzer.analyze(history)

    assert result.best_return_percent == 60.0
    assert result.worst_return_percent == -40.0
    assert result.classification == "UNSTABLE"
