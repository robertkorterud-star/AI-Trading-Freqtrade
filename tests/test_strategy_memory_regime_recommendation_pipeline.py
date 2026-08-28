from datetime import datetime, timezone

from atlas.database.connection import Database
from atlas.database.schema import initialize_database
from atlas.database.strategy_memory_repository import StrategyMemoryRepository
from atlas.trading.strategy_memory import StrategyMemoryRecord
from atlas.trading.strategy_memory_regime_evidence_service import (
    StrategyMemoryRegimeEvidenceService,
)
from atlas.trading.strategy_memory_regime_recommendation_service import (
    StrategyMemoryRegimeRecommendationService,
)


def _record(
    *,
    strategy_name: str,
    total_return: float,
    symbol: str = "BTC-USD",
    regime: str = "LOW_VOLATILITY",
) -> StrategyMemoryRecord:
    return StrategyMemoryRecord(
        symbol=symbol,
        regime=regime,
        strategy_name=strategy_name,
        trade_count=100,
        winning_trades=60,
        losing_trades=40,
        win_rate_percent=60.0,
        average_trade_return_percent=total_return / 100.0,
        total_return_percent=total_return,
        evidence_strength=1.0,
        robust_winner=True,
        updated_at=datetime.now(timezone.utc),
    )


def test_pipeline_produces_recommendation(tmp_path):
    database = Database(
        tmp_path / "strategy_memory.db"
    )
    initialize_database(database)

    repository = StrategyMemoryRepository(database)

    for run_id in ("run-001", "run-002"):
        repository.save(
            _record(
                strategy_name="Momentum",
                total_return=30.0,
            ),
            research_run_id=run_id,
        )

        repository.save(
            _record(
                strategy_name="Trend Following",
                total_return=10.0,
            ),
            research_run_id=run_id,
        )

    evidence_service = StrategyMemoryRegimeEvidenceService(
        repository
    )
    recommendation_service = (
        StrategyMemoryRegimeRecommendationService()
    )

    evidence = evidence_service.analyze(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
    )

    recommendation = recommendation_service.recommend(
        evidence
    )

    assert recommendation.symbol == "BTC-USD"
    assert recommendation.regime == "LOW_VOLATILITY"
    assert recommendation.recommended_strategy == "Momentum"
    assert recommendation.confidence == 20.0
    assert recommendation.independent_run_count == 2
    assert recommendation.robust_winner is True


def test_pipeline_does_not_recommend_without_enough_runs(
    tmp_path,
):
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

    evidence_service = StrategyMemoryRegimeEvidenceService(
        repository
    )
    recommendation_service = (
        StrategyMemoryRegimeRecommendationService()
    )

    evidence = evidence_service.analyze(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
    )

    recommendation = recommendation_service.recommend(
        evidence
    )

    assert recommendation.recommended_strategy is None
    assert recommendation.confidence == 0.0
    assert recommendation.independent_run_count == 1
    assert recommendation.robust_winner is False


def test_pipeline_analyzes_each_symbol_regime_once(tmp_path):
    database = Database(
        tmp_path / "strategy_memory.db"
    )
    initialize_database(database)

    repository = StrategyMemoryRepository(database)

    for run_id in ("run-001", "run-002"):
        repository.save(
            _record(
                strategy_name="Momentum",
                total_return=30.0,
            ),
            research_run_id=run_id,
        )

        repository.save(
            _record(
                strategy_name="Trend Following",
                total_return=10.0,
            ),
            research_run_id=run_id,
        )

    repository.save(
        _record(
            strategy_name="Momentum",
            total_return=25.0,
            regime="HIGH_VOLATILITY",
        ),
        research_run_id="run-001",
    )

    repository.save(
        _record(
            strategy_name="Momentum",
            total_return=25.0,
            regime="HIGH_VOLATILITY",
        ),
        research_run_id="run-002",
    )

    evidence_service = StrategyMemoryRegimeEvidenceService(
        repository
    )

    results = evidence_service.analyze_all()

    assert len(results) == 2
    assert {
        (result.symbol, result.regime)
        for result in results
    } == {
        ("BTC-USD", "LOW_VOLATILITY"),
        ("BTC-USD", "HIGH_VOLATILITY"),
    }
