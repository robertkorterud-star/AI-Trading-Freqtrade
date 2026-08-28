from atlas.models.action import Action
from atlas.trading.strategy_memory_regime_decision_adapter import (
    StrategyMemoryRegimeDecisionAdapter,
)
from atlas.trading.strategy_memory_regime_recommendation_service import (
    StrategyMemoryRegimeRecommendation,
)


def _recommendation(
    *,
    strategy: str | None,
    confidence: float = 20.0,
    independent_run_count: int = 2,
    robust_winner: bool = True,
) -> StrategyMemoryRegimeRecommendation:
    return StrategyMemoryRegimeRecommendation(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        recommended_strategy=strategy,
        confidence=confidence,
        independent_run_count=independent_run_count,
        robust_winner=robust_winner,
    )


def test_recommendation_is_adapted_without_creating_trade_action():
    adapter = StrategyMemoryRegimeDecisionAdapter()

    result = adapter.adapt(
        _recommendation(
            strategy="Momentum",
        )
    )

    assert result.symbol == "BTC-USD"
    assert result.regime == "LOW_VOLATILITY"
    assert result.strategy == "Momentum"
    assert result.action == Action.HOLD
    assert result.confidence == 20.0
    assert result.independent_run_count == 2
    assert result.robust_winner is True


def test_missing_recommendation_remains_hold():
    adapter = StrategyMemoryRegimeDecisionAdapter()

    result = adapter.adapt(
        _recommendation(
            strategy=None,
            confidence=0.0,
            independent_run_count=1,
            robust_winner=False,
        )
    )

    assert result.strategy is None
    assert result.action == Action.HOLD
    assert result.confidence == 0.0
    assert result.independent_run_count == 1
    assert result.robust_winner is False
