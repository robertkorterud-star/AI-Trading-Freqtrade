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


def test_duplicate_records_do_not_increase_confidence():
    analyzer = StrategyMemoryLongitudinalAnalyzer()

    one_record = (
        _record(research_run_id="run-001"),
    )

    duplicate_records = (
        _record(research_run_id="run-001"),
        _record(research_run_id="run-001"),
        _record(research_run_id="run-001"),
        _record(research_run_id="run-001"),
        _record(research_run_id="run-001"),
    )

    one_result = analyzer.analyze(one_record)
    duplicate_result = analyzer.analyze(duplicate_records)

    assert duplicate_result.independent_run_count == 1
    assert duplicate_result.confidence == one_result.confidence


def test_independent_runs_increase_confidence():
    analyzer = StrategyMemoryLongitudinalAnalyzer()

    two_runs = (
        _record(research_run_id="run-001"),
        _record(research_run_id="run-002"),
    )

    five_runs = tuple(
        _record(research_run_id=f"run-{index:03d}")
        for index in range(1, 6)
    )

    two_result = analyzer.analyze(two_runs)
    five_result = analyzer.analyze(five_runs)

    assert two_result.independent_run_count == 2
    assert five_result.independent_run_count == 5
    assert five_result.confidence > two_result.confidence


def test_duplicate_records_plus_new_run_only_count_new_run():
    analyzer = StrategyMemoryLongitudinalAnalyzer()

    history = (
        _record(research_run_id="run-001"),
        _record(research_run_id="run-001"),
        _record(research_run_id="run-001"),
        _record(research_run_id="run-002"),
    )

    result = analyzer.analyze(history)

    assert result.observation_count == 4
    assert result.independent_run_count == 2
