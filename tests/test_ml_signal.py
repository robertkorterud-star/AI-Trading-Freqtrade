from datetime import datetime

from atlas.algorithms.base import AlgorithmSignal
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
    assert 0.0 <= signal.score <= 1.0
    assert signal.reasoning


def test_ml_signal_is_deterministic_for_same_example():
    producer = MLPredictionSignal(_model())

    first = producer.predict(_example(-1.0))
    second = producer.predict(_example(-1.0))

    assert first == second
