"""Verify the orchestrator uses the canonical RiskManager boundary."""

from atlas.algorithms import AlgorithmSignal, DecisionAction, DecisionOrchestrator
from atlas.models.action import Action
from atlas.risk.manager import RiskManager


def _strong_buy() -> AlgorithmSignal:
    return AlgorithmSignal(
        algorithm="test",
        symbol="BTC-USD",
        timeframe="5m",
        action=Action.BUY,
        score=90.0,
        confidence=0.90,
    )


def test_orchestrator_uses_canonical_risk_manager_for_drawdown_gate():
    orchestrator = DecisionOrchestrator(risk_manager=RiskManager())

    result = orchestrator.decide(
        symbol="BTC-USD",
        signals=[_strong_buy()],
        price=100_000.0,
        equity=10_000.0,
        drawdown_pct=25.0,
    )

    assert result.decision.action is DecisionAction.HOLD
    assert result.decision.reason == "canonical decision: hold"

    assessment = orchestrator.decision_engine.last_risk_assessment
    assert assessment is not None
    assert assessment.allowed is False
    assert any("drawdown" in reason.lower() for reason in assessment.reasons)
