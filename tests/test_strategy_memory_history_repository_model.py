from datetime import datetime, timezone

from atlas.database.connection import Database
from atlas.database.schema import initialize_database
from atlas.trading.strategy_memory_history_record import (
    StrategyMemoryHistoryRecord,
)
from atlas.database.strategy_memory_repository import (
    StrategyMemoryRepository,
)
from atlas.trading.strategy_memory import StrategyMemoryRecord


def _record():
    return StrategyMemoryRecord(
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
        updated_at=datetime.now(timezone.utc),
    )


def test_history_returns_history_records(tmp_path):

    database = Database(
        tmp_path / "strategy_memory.db"
    )

    initialize_database(database)

    repository = StrategyMemoryRepository(
        database
    )

    repository.save(
        _record(),
        research_run_id="run-001",
    )

    history = repository.history(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
    )

    assert len(history) == 1

    record = history[0]

    assert isinstance(
        record,
        StrategyMemoryHistoryRecord,
    )

    assert record.research_run_id == "run-001"
    assert record.total_return_percent == 40.0
