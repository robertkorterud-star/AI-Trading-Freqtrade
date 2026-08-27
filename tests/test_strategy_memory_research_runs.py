from datetime import datetime, timezone

from atlas.database.connection import Database
from atlas.database.schema import initialize_database
from atlas.database.strategy_memory_repository import (
    StrategyMemoryRepository,
)
from atlas.trading.strategy_memory import StrategyMemoryRecord


def _record(
    *,
    total_return=20.0,
    updated_at=None,
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
            updated_at
            or datetime.now(timezone.utc)
        ),
    )


def test_history_records_have_distinct_research_runs(
    tmp_path,
):
    database = Database(
        tmp_path / "strategy_memory.db"
    )

    initialize_database(database)

    repository = StrategyMemoryRepository(
        database
    )

    first = _record(total_return=20.0)
    second = _record(total_return=35.0)

    first_run = repository.save_history(
        first,
        research_run_id="run-001",
    )

    second_run = repository.save_history(
        second,
        research_run_id="run-002",
    )

    assert first_run == "run-001"
    assert second_run == "run-002"

    history = repository.history(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
    )

    assert len(history) == 2
    assert [
        record.total_return_percent
        for record in history
    ] == [20.0, 35.0]


def test_same_strategy_can_exist_once_per_research_run(
    tmp_path,
):
    database = Database(
        tmp_path / "strategy_memory.db"
    )

    initialize_database(database)

    repository = StrategyMemoryRepository(
        database
    )

    repository.save_history(
        _record(total_return=10.0),
        research_run_id="run-001",
    )

    repository.save_history(
        _record(total_return=30.0),
        research_run_id="run-002",
    )

    assert repository.history_count() == 2


def test_research_run_id_is_required(tmp_path):

    database = Database(
        tmp_path / "strategy_memory.db"
    )

    initialize_database(database)

    repository = StrategyMemoryRepository(
        database
    )

    try:
        repository.save_history(
            _record(),
            research_run_id="",
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected ValueError"
        )
