from datetime import datetime, timedelta, timezone

from atlas.database.connection import Database
from atlas.database.schema import initialize_database
from atlas.database.strategy_memory_repository import (
    StrategyMemoryRepository,
)
from atlas.trading.strategy_memory import StrategyMemoryRecord
from atlas.trading.strategy_memory_history_service import (
    StrategyMemoryHistoryService,
)


def _record(
    *,
    total_return,
    days_ago,
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


def test_service_analyzes_persisted_history(tmp_path):

    database = Database(
        tmp_path / "strategy_memory.db"
    )

    initialize_database(database)

    repository = StrategyMemoryRepository(
        database
    )

    repository.save(
        _record(
            total_return=20.0,
            days_ago=30,
        )
    )

    repository.save(
        _record(
            total_return=25.0,
            days_ago=20,
        )
    )

    repository.save(
        _record(
            total_return=30.0,
            days_ago=10,
        )
    )

    service = StrategyMemoryHistoryService(
        repository
    )

    result = service.analyze(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
    )

    assert result.observation_count == 3
    assert result.average_return_percent == 25.0
    assert result.best_return_percent == 30.0
    assert result.worst_return_percent == 20.0
    assert result.positive_periods == 3
    assert result.positive_period_ratio == 1.0
    assert result.robust_winner_periods == 3
    assert result.classification == "CONSISTENT"


def test_service_returns_insufficient_for_unknown_strategy(
    tmp_path,
):

    database = Database(
        tmp_path / "strategy_memory.db"
    )

    initialize_database(database)

    repository = StrategyMemoryRepository(
        database
    )

    service = StrategyMemoryHistoryService(
        repository
    )

    result = service.analyze(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
    )

    assert result.observation_count == 0
    assert result.classification == "INSUFFICIENT_DATA"
