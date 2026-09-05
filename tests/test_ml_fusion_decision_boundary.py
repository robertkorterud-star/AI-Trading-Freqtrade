"""Tests that ML signals enter fusion and reach the decision boundary once."""

from types import SimpleNamespace

from atlas.algorithms.base import AlgorithmSignal
from atlas.algorithms.fusion import SignalFusion
from atlas.algorithms.orchestrator import DecisionOrchestrator
from atlas.models.action import Action


def _signal(algorithm: str, action: Action, score: float) -> AlgorithmSignal:
    return AlgorithmSignal(
        symbol="BTC-USD",
        algorithm=algorithm,
        timeframe="1h",
        action=action,
        confidence=0.9,
        score=score,
    )


def test_ml_signal_is_part_of_fusion_input():
    ml = _signal("ml_baseline", Action.BUY, 80.0)
    technical = _signal("technical", Action.BUY, 70.0)

    fused = SignalFusion().combine([ml, technical])

    assert fused.action == Action.BUY
    assert {signal.algorithm for signal in fused.signals} == {
        "ml_baseline",
        "technical",
    }


def test_orchestrator_does_not_double_count_raw_signals_when_fused():
    ml = _signal("ml_baseline", Action.BUY, 80.0)
    technical = _signal("technical", Action.BUY, 70.0)
    fused = SignalFusion().combine([ml, technical])

    captured = []

    class SpyDecisionEngine:
        def evaluate_algorithm_signals(self, signals, **kwargs):
            captured.extend(signals)
            return SimpleNamespace(
                action=Action.BUY,
                confidence=80.0,
                evidence=60.0,
            )

    orchestrator = DecisionOrchestrator(
        decision_engine=SpyDecisionEngine(),
    )

    result = orchestrator.decide(
        symbol="BTC-USD",
        signals=[],
        fusion_result=fused,
    )

    assert result.decision.action.value == "buy"
    assert len(captured) == 1
    assert captured[0].algorithm == "signal_fusion"
    assert captured[0].action == fused.action
    assert captured[0].score == fused.score
