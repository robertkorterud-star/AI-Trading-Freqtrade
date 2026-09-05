"""Tests that fused ML signals reach the canonical decision and risk gates."""

from atlas.algorithms.base import AlgorithmSignal
from atlas.algorithms.fusion import SignalFusion
from atlas.decision.engine import DecisionEngine
from atlas.models.action import Action
from atlas.risk.manager import RiskManager


def _signal(algorithm: str, action: Action, score: float) -> AlgorithmSignal:
    return AlgorithmSignal(
        symbol="BTC-USD",
        algorithm=algorithm,
        timeframe="1h",
        action=action,
        confidence=0.9,
        score=score,
    )


def test_fused_ml_signal_reaches_canonical_decision():
    ml = _signal("ml_baseline", Action.BUY, 90.0)
    technical = _signal("technical", Action.BUY, 80.0)
    fused = SignalFusion().combine([ml, technical])

    decision = DecisionEngine().evaluate_algorithm_signals(
        [],
        fusion_result=fused,
    )

    assert decision.action == Action.BUY
    assert decision.ensemble_action == Action.BUY
    assert decision.analysts == ["signal_fusion"]


def test_risk_gate_can_veto_fused_ml_buy():
    ml = _signal("ml_baseline", Action.BUY, 90.0)
    technical = _signal("technical", Action.BUY, 80.0)
    fused = SignalFusion().combine([ml, technical])

    engine = DecisionEngine(risk_manager=RiskManager())
    decision = engine.evaluate_algorithm_signals(
        [],
        fusion_result=fused,
        price=100_000.0,
        equity=10_000.0,
        drawdown_pct=25.0,
    )

    assert decision.action == Action.HOLD
    assert decision.risk_assessment is not None
    assert decision.risk_assessment.allowed is False
    assert any("drawdown" in reason.lower() for reason in decision.risk_assessment.reasons)
    assert any("final action is HOLD" in reason for reason in decision.reasoning)
