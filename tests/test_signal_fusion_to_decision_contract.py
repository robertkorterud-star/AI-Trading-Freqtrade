from unittest.mock import Mock

from atlas.algorithms.base import AlgorithmSignal
from atlas.algorithms.fusion import SignalFusion
from atlas.algorithms.orchestrator import DecisionOrchestrator
from atlas.models.action import Action


def make_signal(action, score=0.8, confidence=0.9):
    return AlgorithmSignal(
        algorithm="test_algorithm",
        symbol="BTC-USD",
        timeframe="multi",
        action=action,
        score=score,
        confidence=confidence,
    )


def test_signal_fusion_is_handed_to_canonical_decision_engine_as_one_auditable_signal():
    fusion = SignalFusion()
    fusion_result = fusion.combine(
        [
            make_signal(Action.BUY),
            AlgorithmSignal(
                algorithm="test_algorithm_2",
                symbol="BTC-USD",
                timeframe="multi",
                action=Action.BUY,
                score=0.85,
                confidence=0.8,
            ),
            AlgorithmSignal(
                algorithm="test_algorithm_3",
                symbol="BTC-USD",
                timeframe="multi",
                action=Action.HOLD,
                score=0.5,
                confidence=0.7,
            ),
        ]
    )

    decision_engine = Mock()
    decision_engine.evaluate_algorithm_signals.return_value = Mock(
        action=Action.HOLD,
        confidence=0.0,
        evidence=0.0,
    )

    orchestrator = DecisionOrchestrator(decision_engine=decision_engine)
    orchestrator.decide(
        "BTC-USD",
        signals=[],
        fusion_result=fusion_result,
    )

    call = decision_engine.evaluate_algorithm_signals.call_args
    assert call is not None

    decision_inputs = call.args[0]
    assert len(decision_inputs) == 1

    fused_signal = decision_inputs[0]
    assert fused_signal.algorithm == "signal_fusion"
    assert fused_signal.symbol == "BTC-USD"
    assert fused_signal.timeframe == "multi"
    assert fused_signal.action is Action.BUY
    assert fused_signal.score == fusion_result.score
    assert fused_signal.confidence == fusion_result.confidence / 100.0
    assert fused_signal.reasoning == fusion_result.reasoning


def test_signal_fusion_preserves_original_algorithm_signals_for_audit():
    source_signals = [
        make_signal(Action.BUY),
        AlgorithmSignal(
            algorithm="test_algorithm_2",
            symbol="BTC-USD",
            timeframe="multi",
            action=Action.SELL,
            score=0.8,
            confidence=0.9,
        ),
    ]

    fusion_result = SignalFusion().combine(source_signals)

    assert fusion_result.signals == tuple(source_signals)
    assert [signal.algorithm for signal in fusion_result.signals] == [
        "test_algorithm",
        "test_algorithm_2",
    ]


def test_signal_fusion_sell_preserves_directional_score_semantics():
    fusion = SignalFusion()

    fusion_result = fusion.combine(
        [
            AlgorithmSignal(
                algorithm="sell_1",
                symbol="BTC-USD",
                timeframe="multi",
                action=Action.SELL,
                score=20.0,
                confidence=0.90,
            ),
            AlgorithmSignal(
                algorithm="sell_2",
                symbol="BTC-USD",
                timeframe="multi",
                action=Action.SELL,
                score=30.0,
                confidence=0.90,
            ),
            AlgorithmSignal(
                algorithm="hold",
                symbol="BTC-USD",
                timeframe="multi",
                action=Action.HOLD,
                score=50.0,
                confidence=0.70,
            ),
        ]
    )

    assert fusion_result.action is Action.SELL
    assert fusion_result.score < 50.0
