from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult
from atlas.trading.strategy_memory_regime_decision_adapter import (
    StrategyMemoryRegimeDecision,
    StrategyMemoryRegimeDecisionAdapter,
)
from atlas.trading.strategy_memory_regime_recommendation_service import (
    StrategyMemoryRegimeRecommendation,
)


def make_recommendation(
    strategy="Momentum",
    confidence=80.0,
    independent_run_count=8,
    robust_winner=True,
):
    return StrategyMemoryRegimeRecommendation(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        recommended_strategy=strategy,
        confidence=confidence,
        independent_run_count=independent_run_count,
        robust_winner=robust_winner,
    )


def make_decision(action=Action.BUY):
    return DecisionResult(
        symbol="BTC-USD",
        action=action,
        confidence=85.0,
        evidence=90.0,
        robustness=82.0,
        decision_margin=25.0,
    )


def test_regime_recommendation_is_represented_without_creating_trade_signal():
    recommendation = make_recommendation()

    result = StrategyMemoryRegimeDecisionAdapter().adapt(
        recommendation
    )

    assert isinstance(
        result,
        StrategyMemoryRegimeDecision,
    )
    assert result.strategy == "Momentum"
    assert result.action == Action.HOLD
    assert result.robust_winner is True


def test_existing_buy_decision_is_not_overridden_by_regime_strategy():
    decision = make_decision(Action.BUY)
    recommendation = make_recommendation()

    # Regime memory is contextual evidence only.
    assert decision.action == Action.BUY
    assert recommendation.recommended_strategy == "Momentum"


def test_missing_regime_recommendation_is_safe():
    result = StrategyMemoryRegimeDecisionAdapter().adapt(
        make_recommendation(
            strategy=None,
            confidence=0.0,
            independent_run_count=1,
            robust_winner=False,
        )
    )

    assert result.action == Action.HOLD
    assert result.strategy is None
    assert result.robust_winner is False
