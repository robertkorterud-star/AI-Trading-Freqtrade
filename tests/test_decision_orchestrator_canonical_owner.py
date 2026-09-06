from types import SimpleNamespace

from atlas.algorithms.base import AlgorithmSignal
from atlas.algorithms.orchestrator import DecisionOrchestrator
from atlas.models.action import Action


class CapturingDecisionEngine:
    """Minimal test double for the canonical DecisionEngine boundary."""

    def __init__(self):
        self.calls = []

    def evaluate_algorithm_signals(self, signals, **kwargs):
        self.calls.append((list(signals), kwargs))
        return SimpleNamespace(
            action=Action.BUY,
            confidence=80.0,
            evidence=90.0,
        )


def test_orchestrator_delegates_final_decision_to_canonical_engine():
    engine = CapturingDecisionEngine()
    signal = AlgorithmSignal(
        algorithm="test_algorithm",
        symbol="BTC-USD",
        timeframe="5m",
        action=Action.BUY,
        score=0.90,
        confidence=0.90,
    )

    result = DecisionOrchestrator(decision_engine=engine).decide(
        symbol="BTC-USD",
        signals=[signal],
        price=100.0,
        equity=10_000.0,
        current_exposure_pct=5.0,
        drawdown_pct=2.0,
    )

    assert len(engine.calls) == 1
    received_signals, kwargs = engine.calls[0]
    assert received_signals == [signal]
    assert kwargs["price"] == 100.0
    assert kwargs["equity"] == 10_000.0
    assert kwargs["current_exposure_pct"] == 5.0
    assert kwargs["drawdown_pct"] == 2.0
    assert result.canonical_decision.action is Action.BUY
    assert result.decision.action.value == "buy"
