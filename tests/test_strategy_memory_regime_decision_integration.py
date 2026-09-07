from types import SimpleNamespace

from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult
from atlas.trading.strategy_memory_regime_decision_adapter import (
    StrategyMemoryRegimeDecision,
    StrategyMemoryRegimeDecisionAdapter,
)
from atlas.trading.strategy_memory_regime_recommendation_service import (
    StrategyMemoryRegimeRecommendation,
)
from atlas.trading.strategy_memory_regime_decision_integration import (
    StrategyMemoryRegimeDecisionIntegration,
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


def test_regime_integration_preserves_newer_decision_fields():
    risk_assessment = SimpleNamespace(status="approved")
    portfolio_assessment = SimpleNamespace(allocation_pct=12.5)
    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=85.0,
        evidence=90.0,
        robustness=82.0,
        decision_margin=25.0,
        expected_return=4.5,
        ensemble_action=Action.BUY,
        ensemble_confidence=91.0,
        risk_assessment=risk_assessment,
        portfolio_assessment=portfolio_assessment,
    )
    regime_decision = StrategyMemoryRegimeDecisionAdapter().adapt(
        make_recommendation()
    )

    result = StrategyMemoryRegimeDecisionIntegration().integrate(
        decision,
        regime_decision,
    )

    assert result.action is Action.BUY
    assert result.expected_return == 4.5
    assert result.ensemble_action is Action.BUY
    assert result.ensemble_confidence == 91.0
    assert result.risk_assessment is risk_assessment
    assert result.portfolio_assessment is portfolio_assessment
    assert result.reasoning[-1] == (
        "Strategy-memory recommendation is supported "
        "by a robust historical regime winner."
    )
