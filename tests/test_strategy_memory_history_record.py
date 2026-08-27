from datetime import datetime, timezone

from atlas.trading.strategy_memory_history_record import (
    StrategyMemoryHistoryRecord,
)


def test_history_record_contains_research_run_id():

    recorded_at = datetime.now(timezone.utc)

    record = StrategyMemoryHistoryRecord(
        research_run_id="run-001",
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
        trade_count=20,
        winning_trades=15,
        losing_trades=5,
        win_rate_percent=75.0,
        average_trade_return_percent=2.0,
        total_return_percent=40.0,
        evidence_strength="STRONG",
        robust_winner=True,
        recorded_at=recorded_at,
    )

    assert record.research_run_id == "run-001"
    assert record.symbol == "BTC-USD"
    assert record.regime == "LOW_VOLATILITY"
    assert record.strategy_name == "Momentum"
    assert record.total_return_percent == 40.0
    assert record.recorded_at == recorded_at


def test_history_record_is_immutable():

    record = StrategyMemoryHistoryRecord(
        research_run_id="run-001",
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
        trade_count=20,
        winning_trades=15,
        losing_trades=5,
        win_rate_percent=75.0,
        average_trade_return_percent=2.0,
        total_return_percent=40.0,
        evidence_strength="STRONG",
        robust_winner=True,
        recorded_at=datetime.now(timezone.utc),
    )

    try:
        record.total_return_percent = 50.0
    except AttributeError:
        pass
    else:
        raise AssertionError(
            "History records must be immutable."
        )
