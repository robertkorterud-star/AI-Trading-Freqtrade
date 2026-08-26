from datetime import datetime

from atlas.trading.prediction_record import (
    PredictionRecord,
)
from atlas.trading.prediction_training_dataset import (
    PredictionTrainingDataset,
)


def _prediction(
    *,
    evaluated=True,
    correct=True,
    features=None,
):

    return PredictionRecord(
        symbol="BTC-USD",
        action="BUY",
        confidence=90.0,
        evidence=0.9,
        price_usd=100000.0,
        timestamp=datetime.now(),
        features=(
            features
            if features is not None
            else {
                "trend": 1.0,
                "momentum": 1.0,
                "rsi_signal": 1.0,
                "macd_signal": 1.0,
            }
        ),
        evaluated=evaluated,
        correct=correct,
    )


def test_dataset_builds_from_evaluated_prediction():

    result = PredictionTrainingDataset().build(
        [_prediction()]
    )

    assert len(result) == 1

    example = result[0]

    assert example.features["trend"] == 1.0
    assert example.features["momentum"] == 1.0
    assert example.outcome == 1.0

    assert example.symbol == "BTC-USD"
    assert example.action == "BUY"


def test_dataset_marks_incorrect_prediction_zero():

    result = PredictionTrainingDataset().build(
        [
            _prediction(
                correct=False
            )
        ]
    )

    assert len(result) == 1
    assert result[0].outcome == 0.0


def test_dataset_ignores_unevaluated_predictions():

    result = PredictionTrainingDataset().build(
        [
            _prediction(
                evaluated=False
            )
        ]
    )

    assert result == []


def test_dataset_ignores_predictions_without_outcome():

    prediction = _prediction()

    prediction.correct = None

    result = PredictionTrainingDataset().build(
        [prediction]
    )

    assert result == []


def test_dataset_ignores_predictions_without_features():

    result = PredictionTrainingDataset().build(
        [
            _prediction(
                features={}
            )
        ]
    )

    assert result == []


def test_dataset_copies_features():

    prediction = _prediction()

    result = PredictionTrainingDataset().build(
        [prediction]
    )

    result[0].features["trend"] = -1.0

    assert prediction.features["trend"] == 1.0
