from atlas.database.connection import Database
from atlas.database.schema import initialize_database
from atlas.database.strategy_memory_repository import (
    StrategyMemoryRepository,
)
from atlas.trading.strategy_memory import StrategyMemory
from atlas.trading.strategy_memory_regime_evidence_service import (
    StrategyMemoryRegimeEvidenceService,
)


def _record(
    *,
    strategy_name: str,
    total_return: float,
):
    memory = StrategyMemory()

    return memory.record(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name=strategy_name,
        trade_count=20,
        winning_trades=14,
        losing_trades=6,
        average_trade_return_percent=(
            total_return / 20.0
        ),
        total_return_percent=total_return,
        evidence_strength="STRONG",
        robust_winner=True,
    )


def test_analyze_loads_all_strategies_for_regime(tmp_path):
    database = Database(
        tmp_path / "strategy_memory.db"
    )
    initialize_database(database)

    repository = StrategyMemoryRepository(database)

    repository.save(
        _record(
            strategy_name="Momentum",
            total_return=30.0,
        ),
        research_run_id="run-001",
    )

    repository.save(
        _record(
            strategy_name="Trend Following",
            total_return=15.0,
        ),
        research_run_id="run-001",
    )

    repository.save(
        _record(
            strategy_name="Momentum",
            total_return=32.0,
        ),
        research_run_id="run-002",
    )

    repository.save(
        _record(
            strategy_name="Trend Following",
            total_return=16.0,
        ),
        research_run_id="run-002",
    )

    service = StrategyMemoryRegimeEvidenceService(
        repository
    )

    result = service.analyze(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
    )

    assert result.recommended_strategy == "Momentum"
    assert result.robust_winner is True
    assert result.independent_run_count == 2


def test_analyze_without_history_returns_no_winner(tmp_path):
    database = Database(
        tmp_path / "strategy_memory.db"
    )
    initialize_database(database)

    repository = StrategyMemoryRepository(database)

    service = StrategyMemoryRegimeEvidenceService(
        repository
    )

    result = service.analyze(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
    )

    assert result.recommended_strategy is None
    assert result.confidence == 0.0
    assert result.independent_run_count == 0
    assert result.robust_winner is False


def test_analyze_all_returns_deterministic_results(tmp_path):
    database = Database(
        tmp_path / "strategy_memory.db"
    )
    initialize_database(database)

    repository = StrategyMemoryRepository(database)

    repository.save(
        _record(
            strategy_name="Momentum",
            total_return=30.0,
        ),
        research_run_id="run-001",
    )

    repository.save(
        _record(
            strategy_name="Trend Following",
            total_return=15.0,
        ),
        research_run_id="run-001",
    )

    service = StrategyMemoryRegimeEvidenceService(
        repository
    )

    results = service.analyze_all()

    assert len(results) == 1
    assert results[0].symbol == "BTC-USD"
    assert results[0].regime == "LOW_VOLATILITY"
