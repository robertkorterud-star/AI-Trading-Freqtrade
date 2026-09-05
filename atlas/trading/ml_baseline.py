"""
ATLAS ML baseline.

A small, deterministic baseline for evaluating whether the
prediction feature vector contains useful information.

This module does NOT generate trading decisions.
"""

from dataclasses import dataclass
from typing import Protocol

from atlas.trading.prediction_training_dataset import (
    PredictionTrainingExample,
)


class PredictionFeatureExample(Protocol):
    """Minimal feature contract required for ML inference."""

    features: dict[str, float]


@dataclass(frozen=True, slots=True)
class MLEvaluationResult:
    train_examples: int
    test_examples: int
    accuracy: float
    baseline_accuracy: float
    improvement: float
    predictions: tuple[float, ...]


class LogisticRegressionBaseline:
    """
    Lightweight logistic-regression baseline.

    Uses only the Python standard library so the first ML
    layer does not introduce a heavyweight dependency.
    """

    def __init__(
        self,
        learning_rate: float = 0.05,
        epochs: int = 500,
    ):
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.weights: list[float] = []
        self.feature_names: tuple[str, ...] = ()
        self.bias = 0.0

    def fit(
        self,
        examples: list[PredictionTrainingExample],
    ):
        if not examples:
            raise ValueError(
                "Cannot train on an empty dataset."
            )

        names = sorted(
            {
                name
                for example in examples
                for name in example.features
            }
        )

        if not names:
            raise ValueError(
                "Training examples contain no features."
            )

        self.feature_names = tuple(names)
        self.weights = [0.0] * len(names)
        self.bias = 0.0

        vectors = [
            [
                float(example.features.get(name, 0.0))
                for name in self.feature_names
            ]
            for example in examples
        ]

        targets = [
            float(example.outcome)
            for example in examples
        ]

        for _ in range(self.epochs):
            gradients = [0.0] * len(names)
            bias_gradient = 0.0

            for vector, target in zip(
                vectors,
                targets,
            ):
                probability = self._sigmoid(
                    self.bias
                    + sum(
                        weight * value
                        for weight, value in zip(
                            self.weights,
                            vector,
                        )
                    )
                )

                error = probability - target

                for index, value in enumerate(
                    vector
                ):
                    gradients[index] += (
                        error * value
                    )

                bias_gradient += error

            count = len(vectors)

            for index in range(len(self.weights)):
                self.weights[index] -= (
                    self.learning_rate
                    * gradients[index]
                    / count
                )

            self.bias -= (
                self.learning_rate
                * bias_gradient
                / count
            )

        return self

    def predict_probability(
        self,
        example: PredictionFeatureExample,
    ) -> float:

        if not self.weights:
            raise RuntimeError(
                "Model has not been fitted."
            )

        values = [
            float(example.features.get(name, 0.0))
            for name in self.feature_names
        ]

        if len(values) != len(self.weights):
            raise ValueError(
                "Feature vector does not match "
                "the fitted model."
            )

        score = self.bias + sum(
            weight * value
            for weight, value in zip(
                self.weights,
                values,
            )
        )

        return self._sigmoid(score)

    def predict(
        self,
        example: PredictionFeatureExample,
    ) -> float:

        return (
            1.0
            if self.predict_probability(example)
            >= 0.5
            else 0.0
        )

    @staticmethod
    def _sigmoid(value: float) -> float:
        if value >= 0:
            exponent = _safe_exp(-value)
            return 1.0 / (1.0 + exponent)

        exponent = _safe_exp(value)
        return exponent / (1.0 + exponent)


def time_split(
    examples: list[PredictionTrainingExample],
    train_ratio: float = 0.8,
) -> tuple[
    list[PredictionTrainingExample],
    list[PredictionTrainingExample],
]:

    if not 0.0 < train_ratio < 1.0:
        raise ValueError(
            "train_ratio must be between 0 and 1."
        )

    ordered = sorted(
        examples,
        key=lambda example: example.timestamp,
    )

    split = int(
        len(ordered) * train_ratio
    )

    if split <= 0 or split >= len(ordered):
        raise ValueError(
            "Dataset is too small for the requested split."
        )

    return (
        ordered[:split],
        ordered[split:],
    )


def evaluate_baseline(
    examples: list[PredictionTrainingExample],
    train_ratio: float = 0.8,
    ):
    train, test = time_split(examples, train_ratio)
    model = LogisticRegressionBaseline()
    model.fit(train)

    predictions = tuple(
        model.predict(example)
        for example in test
    )

    correct = sum(
        prediction == example.outcome
        for prediction, example in zip(
            predictions,
            test,
        )
    )

    accuracy = correct / len(test)

    positives = sum(
        example.outcome >= 0.5
        for example in train
    )
    baseline_class = (
        1.0
        if positives >= len(train) / 2
        else 0.0
    )

    baseline_correct = sum(
        example.outcome == baseline_class
        for example in test
    )
    baseline_accuracy = (
        baseline_correct / len(test)
    )

    return MLEvaluationResult(
        train_examples=len(train),
        test_examples=len(test),
        accuracy=accuracy,
        baseline_accuracy=baseline_accuracy,
        improvement=accuracy - baseline_accuracy,
        predictions=predictions,
    )


def _safe_exp(value: float) -> float:
    if value > 60:
        return 1e26
    if value < -60:
        return 0.0

    import math

    return math.exp(value)
