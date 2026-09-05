from datetime import datetime

from atlas.algorithms.base import AlgorithmSignal
from atlas.algorithms.fusion import SignalFusion
from atlas.models.action import Action
from atlas.trading.ml_baseline import LogisticRegressionBaseline
from atlas.trading.ml_signal import MLPredictionSignal
from atlas.trading.prediction_training_dataset import PredictionTrainingExample


def _example(trend: float) -> PredictionTrainingExample:
    return PredictionTrainingExample(
        features={"trend": trend},
        outcome=1.0,
        symbol="BTC-USD",
        action="BUY",
        timestamp=datetime(2026, 1, 1),
    )


def _model() -> LogisticRegressionBaseline:
    model = LogisticRegressionBaseline(
        learning_rate=0.1,
        epochs=1000,
    )
    model.fit(
        [
            _example(-1.0),
            PredictionTrainingExample(
                features={"trend": 1.0},
                outcome=0.0,
                symbol="BTC-USD",
                action="BUY",
                timestamp=datetime(2026, 1, 2),
            ),
        ]
    )
    return model


def test_ml_signal_produces_algorithm_signal():
    signal = MLPredictionSignal(_model()).predict(_example(-1.0))

    assert isinstance(signal, AlgorithmSignal)
    assert signal.symbol == "BTC-USD"
    assert signal.algorithm == "ml_baseline"
    assert signal.action in {Action.BUY, Action.SELL}
    assert 0.0 <= signal.confidence <= 1.0
    assert 0.0 <= signal.score <= 100.0
    assert signal.reasoning


def test_ml_signal_score_matches_canonical_fusion_scale():
    signal = MLPredictionSignal(_model()).predict(_example(-1.0))
    probability = float(signal.reasoning[0].split("=")[1])

    assert signal.score == 50.0 + (probability - 0.5) * 100.0


def test_ml_signal_can_enter_signal_fusion_without_scale_distortion():
    ml_signal = MLPredictionSignal(_model()).predict(_example(-1.0))
    companion = AlgorithmSignal(
        algorithm="companion",
        symbol="BTC-USD",
        timeframe="model",
        action=Action.BUY,
        score=80.0,
        confidence=0.8,
    )

    fused = SignalFusion().combine([ml_signal, companion])

    assert fused.action is Action.BUY
    assert 0.0 <= fused.score <= 100.0
    assert fused.score > 50.0


def test_ml_signal_is_deterministic_for_same_example():
    producer = MLPredictionSignal(_model())

    first = producer.predict(_example(-1.0))
    second = producer.predict(_example(-1.0))

    assert first == second
