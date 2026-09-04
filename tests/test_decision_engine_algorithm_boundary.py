import pytest

from atlas.algorithms.base import AlgorithmSignal
from atlas.algorithms.fusion import FusionResult
from atlas.algorithms.orchestrator import DecisionOrchestrator
from atlas.decision.engine import DecisionEngine
from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult as CanonicalDecisionResult


def test_algorithm_and_fusion_signals_enter_canonical_decision_engine():
    algorithm_signal = AlgorithmSignal(
        algorithm="trend",
        symbol="BTC-USD",
        timeframe="5m",
        action=Action.BUY,
        score=90.0,
        confidence=0.90,
        reasoning=["Strong trend confirmation."],
    )
    fusion_result = FusionResult(
        symbol="BTC-USD",
        timeframe="5m",
        action=Action.BUY,
        score=90.0,
        confidence=90.0,
        agreement=1.0,
        signals=(algorithm_signal,),
        reasoning=["Fusion confirms BUY."],
    )

    decision = DecisionEngine().evaluate_algorithm_signals(
        [algorithm_signal],
        fusion_result=fusion_result,
    )

    assert decision.action is Action.BUY
    assert decision.ensemble_action is Action.BUY
    assert decision.ensemble_confidence == 100.0
    assert decision.analysts == ["algorithm:trend", "signal_fusion"]
    assert any("Strong trend confirmation." in reason for reason in decision.reasoning)
    assert any("Fusion confirms BUY." in reason for reason in decision.reasoning)


def test_orchestrator_delegates_final_decision_to_canonical_engine():
    class CapturingDecisionEngine:
        def __init__(self):
            self.received_signals = None

        def evaluate_algorithm_signals(self, signals):
            self.received_signals = list(signals)
            return CanonicalDecisionResult(
                symbol="BTC-USD",
                action=Action.BUY,
                confidence=90.0,
                evidence=80.0,
            )

    engine = CapturingDecisionEngine()
    signal = AlgorithmSignal(
        algorithm="trend",
        symbol="BTC-USD",
        timeframe="5m",
        action=Action.BUY,
        score=90.0,
        confidence=0.90,
    )

    result = DecisionOrchestrator(
        decision_engine=engine,
    ).decide(
        symbol="BTC-USD",
        signals=[signal],
    )

    assert engine.received_signals == [signal]
    assert result.decision.action.value == "buy"
    assert result.decision.confidence == 0.90
    assert result.decision.score == pytest.approx(0.72)
