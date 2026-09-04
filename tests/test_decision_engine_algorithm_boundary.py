from atlas.algorithms.base import AlgorithmSignal
from atlas.algorithms.fusion import FusionResult
from atlas.decision.engine import DecisionEngine
from atlas.models.action import Action


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
