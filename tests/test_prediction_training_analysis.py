from datetime import datetime

from atlas.trading.prediction_training_analysis import (
    PredictionTrainingAnalyzer,
)
from atlas.trading.prediction_training_dataset import (
    PredictionTrainingExample,
)


def _example(
    *,
    action="BUY",
    outcome=1.0,
    trend=1.0,
    momentum=1.0,
):
    return PredictionTrainingExample(
        features={
            "trend": trend,
            "momentum": momentum,
        },
        outcome=outcome,
        symbol="BTC-USD",
        action=action,
        timestamp=datetime.now(),
    )


def test_empty_dataset_is_not_ml_ready():

    result = PredictionTrainingAnalyzer().analyze([])

    assert result.total_examples == 0
    assert result.accuracy == 0.0
    assert result.feature_coverage == 0.0
    assert result.ml_ready is False


def test_analyzer_counts_predictions_and_outcomes():

    examples = [
        _example(
            action="BUY",
            outcome=1.0,
        ),
        _example(
            action="BUY",
            outcome=0.0,
            trend=-1.0,
        ),
        _example(
            action="SELL",
            outcome=1.0,
            momentum=-1.0,
        ),
    ]

    result = PredictionTrainingAnalyzer().analyze(
        examples
    )

    assert result.total_examples == 3
    assert result.buy_examples == 2
    assert result.sell_examples == 1

    assert result.positive_outcomes == 2
    assert result.negative_outcomes == 1

    assert result.accuracy == 2 / 3 * 100


def test_analyzer_detects_varying_features():

    examples = [
        _example(
            trend=1.0,
            momentum=1.0,
        ),
        _example(
            trend=-1.0,
            momentum=1.0,
        ),
        _example(
            trend=1.0,
            momentum=-1.0,
        ),
    ]

    result = PredictionTrainingAnalyzer().analyze(
        examples
    )

    assert "trend" in result.varying_features
    assert "momentum" in result.varying_features

    assert result.constant_features == ()


def test_analyzer_detects_constant_features():

    examples = [
        _example(
            trend=1.0,
            momentum=1.0,
        ),
        _example(
            trend=1.0,
            momentum=-1.0,
        ),
    ]

    result = PredictionTrainingAnalyzer().analyze(
        examples
    )

    assert "trend" in result.constant_features
    assert "momentum" in result.varying_features


def test_dataset_with_only_one_action_is_not_ml_ready():

    examples = [
        _example(
            outcome=1.0,
        )
        for _ in range(99)
    ]

    examples.append(
        _example(
            outcome=0.0,
            trend=-1.0,
        )
    )

    result = PredictionTrainingAnalyzer().analyze(
        examples
    )

    assert result.total_examples == 100
    assert result.buy_examples == 100
    assert result.sell_examples == 0
    assert result.ml_ready is False
