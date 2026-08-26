from datetime import datetime, timedelta

from atlas.trading.historical_ml_evaluation import (
    HistoricalMLEvaluator,
)
from atlas.trading.prediction_record import (
    PredictionRecord,
)


def _prediction(
    timestamp,
    *,
    correct=True,
    trend=1.0,
):

    return PredictionRecord(
        symbol="BTC-USD",
        action="BUY",
        confidence=80.0,
        evidence=0.8,
        price_usd=100000.0,
        timestamp=timestamp,
        features={
            "trend": trend,
            "momentum": trend,
        },
        evaluated=True,
        correct=correct,
    )


def _predictions(count=20):

    start = datetime(2026, 1, 1)

    return [
        _prediction(
            start + timedelta(days=index),
            correct=index % 2 == 0,
            trend=(
                1.0
                if index % 2 == 0
                else -1.0
            ),
        )
        for index in range(count)
    ]


def test_historical_evaluator_builds_ml_evaluation():

    result = HistoricalMLEvaluator().evaluate(
        _predictions(20)
    )

    assert result.prediction_count == 20
    assert result.training_examples == 20
    assert result.skipped_predictions == 0

    assert result.evaluation is not None

    assert (
        result.evaluation.train_examples
        == 16
    )

    assert (
        result.evaluation.test_examples
        == 4
    )


def test_historical_evaluator_counts_skipped_predictions():

    predictions = _predictions(10)

    predictions.append(
        PredictionRecord(
            symbol="BTC-USD",
            action="BUY",
            confidence=80.0,
            evidence=0.8,
            price_usd=100000.0,
            timestamp=datetime(2026, 2, 1),
            evaluated=False,
            correct=None,
            features={
                "trend": 1.0,
            },
        )
    )

    result = HistoricalMLEvaluator().evaluate(
        predictions
    )

    assert result.prediction_count == 11
    assert result.training_examples == 10
    assert result.skipped_predictions == 1


def test_historical_evaluator_handles_too_little_data():

    result = HistoricalMLEvaluator().evaluate(
        _predictions(1)
    )

    assert result.prediction_count == 1
    assert result.training_examples == 1
    assert result.evaluation is None


def test_historical_evaluator_does_not_modify_predictions():

    predictions = _predictions(20)

    before = [
        (
            prediction.timestamp,
            prediction.correct,
            dict(prediction.features),
        )
        for prediction in predictions
    ]

    HistoricalMLEvaluator().evaluate(
        predictions
    )

    after = [
        (
            prediction.timestamp,
            prediction.correct,
            dict(prediction.features),
        )
        for prediction in predictions
    ]

    assert after == before
