from atlas.trading.strategy_memory_regime_evidence import (
    StrategyMemoryRegimeEvidenceResult,
)
from atlas.trading.strategy_memory_regime_recommendation_service import (
    StrategyMemoryRegimeRecommendationService,
)


def _result(
    *,
    symbol="BTC-USD",
    regime="LOW_VOLATILITY",
    recommended_strategy=None,
    confidence=0.0,
    independent_run_count=0,
    robust_winner=False,
):
    return StrategyMemoryRegimeEvidenceResult(
        symbol=symbol,
        regime=regime,
        recommended_strategy=recommended_strategy,
        confidence=confidence,
        independent_run_count=independent_run_count,
        robust_winner=robust_winner,
    )


def test_no_robust_evidence_returns_no_recommendation():
    service = StrategyMemoryRegimeRecommendationService()

    result = service.recommend(
        _result(
            recommended_strategy=None,
            confidence=0.0,
            independent_run_count=3,
            robust_winner=False,
        )
    )

    assert result.recommended_strategy is None
    assert result.confidence == 0.0
    assert result.independent_run_count == 3
    assert result.robust_winner is False


def test_robust_evidence_is_promoted_to_recommendation():
    service = StrategyMemoryRegimeRecommendationService()

    result = service.recommend(
        _result(
            recommended_strategy="Momentum",
            confidence=40.0,
            independent_run_count=4,
            robust_winner=True,
        )
    )

    assert result.recommended_strategy == "Momentum"
    assert result.confidence == 40.0
    assert result.independent_run_count == 4
    assert result.robust_winner is True


def test_weak_confidence_is_not_promoted():
    service = StrategyMemoryRegimeRecommendationService(
        minimum_confidence=50.0,
    )

    result = service.recommend(
        _result(
            recommended_strategy="Momentum",
            confidence=40.0,
            independent_run_count=4,
            robust_winner=True,
        )
    )

    assert result.recommended_strategy is None
    assert result.confidence == 40.0
    assert result.independent_run_count == 4
    assert result.robust_winner is False


def test_confidence_threshold_is_inclusive():
    service = StrategyMemoryRegimeRecommendationService(
        minimum_confidence=50.0,
    )

    result = service.recommend(
        _result(
            recommended_strategy="Momentum",
            confidence=50.0,
            independent_run_count=5,
            robust_winner=True,
        )
    )

    assert result.recommended_strategy == "Momentum"
    assert result.confidence == 50.0
    assert result.robust_winner is True


def test_empty_strategy_is_never_recommended():
    service = StrategyMemoryRegimeRecommendationService()

    result = service.recommend(
        _result(
            recommended_strategy="",
            confidence=100.0,
            independent_run_count=10,
            robust_winner=True,
        )
    )

    assert result.recommended_strategy is None
    assert result.confidence == 100.0
    assert result.independent_run_count == 10
    assert result.robust_winner is False
