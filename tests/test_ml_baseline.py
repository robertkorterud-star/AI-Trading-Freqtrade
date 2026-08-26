from datetime import datetime, timedelta

import pytest

from atlas.trading.ml_baseline import (
    LogisticRegressionBaseline,
    evaluate_baseline,
    time_split,
)
from atlas.trading.prediction_training_dataset import (
    PredictionTrainingExample,
)


def _example(
    timestamp,
    *,
    trend,
    outcome,
):
    return PredictionTrainingExample(
        features={
            "trend": float(trend),
        },
        outcome=float(outcome),
        symbol="BTC-USD",
        action="BUY",
        timestamp=timestamp,
    )


def _examples(count=20):
    start = datetime(2026, 1, 1)

    return [
        _example(
            start + timedelta(days=index),
            trend=1.0 if index % 2 else -1.0,
            outcome=1.0 if index % 2 else 0.0,
        )
        for index in range(count)
    ]


def test_time_split_preserves_chronological_order():

    examples = _examples(10)

    train, test = time_split(
        examples,
        train_ratio=0.8,
    )

    assert len(train) == 8
    assert len(test) == 2

    assert train[-1].timestamp < test[0].timestamp


def test_time_split_rejects_invalid_ratio():

    with pytest.raises(ValueError):
        time_split(
            _examples(),
            train_ratio=1.0,
        )


def test_model_requires_training():

    model = LogisticRegressionBaseline()

    with pytest.raises(RuntimeError):
        model.predict_probability(
            _examples(1)[0]
        )


def test_model_learns_simple_relationship():

    examples = _examples(40)

    model = LogisticRegressionBaseline(
        learning_rate=0.1,
        epochs=1000,
    )

    model.fit(examples)

    positive = _example(
        datetime(2027, 1, 1),
        trend=1.0,
        outcome=1.0,
    )

    negative = _example(
        datetime(2027, 1, 2),
        trend=-1.0,
        outcome=0.0,
    )

    assert (
        model.predict_probability(positive)
        > 0.5
    )

    assert (
        model.predict_probability(negative)
        < 0.5
    )


def test_evaluation_uses_future_test_window():

    result = evaluate_baseline(
        _examples(50)
    )

    assert result.train_examples == 40
    assert result.test_examples == 10

    assert 0.0 <= result.accuracy <= 100.0
    assert (
        result.baseline_accuracy
        >= 0.0
    )


def test_baseline_does_not_modify_examples():

    examples = _examples(20)

    before = [
        (
            example.timestamp,
            dict(example.features),
            example.outcome,
        )
        for example in examples
    ]

    evaluate_baseline(examples)

    after = [
        (
            example.timestamp,
            dict(example.features),
            example.outcome,
        )
        for example in examples
    ]

    assert after == before
