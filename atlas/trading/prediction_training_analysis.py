"""
ATLAS Prediction Training Dataset Analysis.

Provides descriptive statistics about the supervised-learning
dataset before any ML model is trained.
"""

from dataclasses import dataclass

from atlas.trading.prediction_training_dataset import (
    PredictionTrainingExample,
)


@dataclass(frozen=True, slots=True)
class PredictionTrainingAnalysis:
    total_examples: int
    buy_examples: int
    sell_examples: int
    positive_outcomes: int
    negative_outcomes: int
    accuracy: float
    feature_coverage: float
    varying_features: tuple[str, ...]
    constant_features: tuple[str, ...]
    ml_ready: bool


class PredictionTrainingAnalyzer:
    """Analyze training data without training a model."""

    def analyze(
        self,
        examples: list[PredictionTrainingExample],
    ) -> PredictionTrainingAnalysis:

        total = len(examples)

        if total == 0:
            return PredictionTrainingAnalysis(
                total_examples=0,
                buy_examples=0,
                sell_examples=0,
                positive_outcomes=0,
                negative_outcomes=0,
                accuracy=0.0,
                feature_coverage=0.0,
                varying_features=(),
                constant_features=(),
                ml_ready=False,
            )

        buy = sum(
            example.action == "BUY"
            for example in examples
        )

        sell = sum(
            example.action == "SELL"
            for example in examples
        )

        positive = sum(
            example.outcome > 0
            for example in examples
        )

        negative = sum(
            example.outcome <= 0
            for example in examples
        )

        accuracy = (
            positive / total * 100.0
        )

        feature_names = sorted(
            {
                name
                for example in examples
                for name in example.features
            }
        )

        varying = []
        constant = []

        for name in feature_names:
            values = {
                example.features.get(name)
                for example in examples
            }

            if len(values) > 1:
                varying.append(name)
            else:
                constant.append(name)

        feature_values = sum(
            len(example.features)
            for example in examples
        )

        expected_values = (
            total * len(feature_names)
        )

        coverage = (
            feature_values
            / expected_values
            * 100.0
            if expected_values
            else 0.0
        )

        ml_ready = (
            total >= 100
            and positive > 0
            and negative > 0
            and len(varying) >= 2
            and coverage >= 90.0
        )

        return PredictionTrainingAnalysis(
            total_examples=total,
            buy_examples=buy,
            sell_examples=sell,
            positive_outcomes=positive,
            negative_outcomes=negative,
            accuracy=accuracy,
            feature_coverage=coverage,
            varying_features=tuple(varying),
            constant_features=tuple(constant),
            ml_ready=ml_ready,
        )
