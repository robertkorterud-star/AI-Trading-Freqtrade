from datetime import datetime, timezone

from atlas.trading.strategy_memory_history_record import (
    StrategyMemoryHistoryRecord,
)
from atlas.trading.strategy_memory_longitudinal_analyzer import (
    StrategyMemoryLongitudinalAnalyzer,
)


def _record(
    *,
    research_run_id,
    total_return=20.0,
):
    return StrategyMemoryHistoryRecord(
        research_run_id=research_run_id,
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
        recorded_at=datetime.now(timezone.utc),
    )


def test_counts_unique_research_runs():

    analyzer = StrategyMemoryLongitudinalAnalyzer()

    history = (
        _record(
            research_run_id="run-001",
            total_return=20.0,
        ),
        _record(
            research_run_id="run-001",
            total_return=20.0,
        ),
        _record(
            research_run_id="run-002",
            total_return=25.0,
        ),
    )

    result = analyzer.analyze(history)

    assert result.observation_count == 3
    assert result.independent_run_count == 2


def test_duplicate_records_from_same_run_do_not_increase_run_count():

    analyzer = StrategyMemoryLongitudinalAnalyzer()

    history = (
        _record(research_run_id="run-001"),
        _record(research_run_id="run-001"),
        _record(research_run_id="run-001"),
    )

    result = analyzer.analyze(history)

    assert result.observation_count == 3
    assert result.independent_run_count == 1
