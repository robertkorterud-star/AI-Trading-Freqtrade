from datetime import datetime

from atlas.database.connection import Database
from atlas.database.schema import initialize_database
from atlas.database.strategy_memory_repository import (
    StrategyMemoryRepository,
)
from atlas.trading.strategy_memory import (
    StrategyMemoryRecord,
)


def _record(
    strategy="Momentum",
    regime="LOW_VOLATILITY",
    trade_count=20,
    total_return=40.0,
):
    return StrategyMemoryRecord(
        symbol="BTC-USD",
        regime=regime,
        strategy_name=strategy,
        trade_count=trade_count,
        winning_trades=15,
        losing_trades=5,
        win_rate_percent=75.0,
        average_trade_return_percent=2.0,
        total_return_percent=total_return,
        evidence_strength="STRONG",
        robust_winner=True,
        updated_at=datetime.now(),
    )


def test_save_creates_history_record(tmp_path):
    database = Database(
        tmp_path / "strategy_memory.db"
    )

    initialize_database(database)

    repository = StrategyMemoryRepository(database)

    repository.save(_record())

    history = repository.history(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
    )

    assert len(history) == 1
    assert history[0].trade_count == 20
    assert history[0].total_return_percent == 40.0


def test_multiple_saves_preserve_history(tmp_path):
    database = Database(
        tmp_path / "strategy_memory.db"
    )

    initialize_database(database)

    repository = StrategyMemoryRepository(database)

    repository.save(
        _record(
            trade_count=10,
            total_return=10.0,
        )
    )

    repository.save(
        _record(
            trade_count=20,
            total_return=40.0,
        )
    )

    history = repository.history(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
    )

    assert len(history) == 2

    assert [
        record.trade_count
        for record in history
    ] == [10, 20]


def test_current_record_still_updates(tmp_path):
    database = Database(
        tmp_path / "strategy_memory.db"
    )

    initialize_database(database)

    repository = StrategyMemoryRepository(database)

    repository.save(
        _record(
            trade_count=10,
            total_return=10.0,
        )
    )

    repository.save(
        _record(
            trade_count=20,
            total_return=40.0,
        )
    )

    current = repository.get(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
    )

    assert current is not None
    assert current.trade_count == 20
    assert current.total_return_percent == 40.0

    assert repository.history_count() == 2
