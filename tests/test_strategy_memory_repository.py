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
):
    return StrategyMemoryRecord(
        symbol="BTC-USD",
        regime=regime,
        strategy_name=strategy,
        trade_count=20,
        winning_trades=15,
        losing_trades=5,
        win_rate_percent=75.0,
        average_trade_return_percent=2.0,
        total_return_percent=40.0,
        evidence_strength="STRONG",
        robust_winner=True,
        updated_at=datetime.now(),
    )


def test_save_and_get_roundtrip(tmp_path):
    database = Database(
        tmp_path / "strategy_memory.db"
    )

    initialize_database(database)

    repository = StrategyMemoryRepository(
        database
    )

    record = _record()

    repository.save(record)

    restored = repository.get(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
    )

    assert restored is not None
    assert restored.symbol == "BTC-USD"
    assert restored.regime == "LOW_VOLATILITY"
    assert restored.strategy_name == "Momentum"
    assert restored.trade_count == 20
    assert restored.win_rate_percent == 75.0
    assert restored.robust_winner is True


def test_for_regime_returns_sorted_records(tmp_path):
    database = Database(
        tmp_path / "strategy_memory.db"
    )

    initialize_database(database)

    repository = StrategyMemoryRepository(
        database
    )

    repository.save(
        _record("Trend Following")
    )

    repository.save(
        _record("Momentum")
    )

    records = repository.for_regime(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
    )

    assert [
        record.strategy_name
        for record in records
    ] == [
        "Momentum",
        "Trend Following",
    ]


def test_get_all_and_count(tmp_path):
    database = Database(
        tmp_path / "strategy_memory.db"
    )

    initialize_database(database)

    repository = StrategyMemoryRepository(
        database
    )

    repository.save(_record("Momentum"))
    repository.save(
        _record(
            "Mean Reversion",
            "RANGING",
        )
    )

    assert repository.count() == 2
    assert len(repository.get_all()) == 2


def test_save_updates_existing_record(tmp_path):
    database = Database(
        tmp_path / "strategy_memory.db"
    )

    initialize_database(database)

    repository = StrategyMemoryRepository(
        database
    )

    repository.save(_record())

    updated = StrategyMemoryRecord(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
        trade_count=30,
        winning_trades=22,
        losing_trades=8,
        win_rate_percent=73.33,
        average_trade_return_percent=1.8,
        total_return_percent=54.0,
        evidence_strength="STRONG",
        robust_winner=True,
        updated_at=datetime.now(),
    )

    repository.save(updated)

    restored = repository.get(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
    )

    assert restored is not None
    assert restored.trade_count == 30
    assert repository.count() == 1


def test_clear_removes_records(tmp_path):
    database = Database(
        tmp_path / "strategy_memory.db"
    )

    initialize_database(database)

    repository = StrategyMemoryRepository(
        database
    )

    repository.save(_record())

    assert repository.count() == 1

    repository.clear()

    assert repository.count() == 0
    assert repository.get_all() == ()


def test_save_and_get_preserves_subsecond_updated_at(tmp_path):
    database = Database(
        tmp_path / "strategy_memory.db"
    )
    initialize_database(database)
    repository = StrategyMemoryRepository(database)

    updated_at = datetime(
        2026, 9, 28, 8, 0, 0, 900000
    )

    record = _record()
    record.updated_at = updated_at

    repository.save(record)

    restored = repository.get(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
    )

    assert restored is not None
    assert restored.updated_at == updated_at
