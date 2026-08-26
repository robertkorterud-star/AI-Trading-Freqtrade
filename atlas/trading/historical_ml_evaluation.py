"""
ATLAS Historical ML Evaluation.

Evaluates the ML baseline against historical, already-evaluated
ATLAS predictions.

This module never creates or changes trading decisions.
"""

from dataclasses import dataclass

from atlas.trading.ml_baseline import (
    MLEvaluationResult,
    evaluate_baseline,
)
from atlas.trading.prediction_training_dataset import (
    PredictionTrainingDataset,
)
from atlas.trading.prediction_record import PredictionRecord


@dataclass(frozen=True, slots=True)
class HistoricalMLEvaluation:
    prediction_count: int
    training_examples: int
    skipped_predictions: int
    evaluation: MLEvaluationResult | None


class HistoricalMLEvaluator:
    """Evaluate ML performance on historical predictions."""

    def __init__(
        self,
        dataset: PredictionTrainingDataset | None = None,
    ):
        self.dataset = (
            dataset
            or PredictionTrainingDataset()
        )

    def evaluate(
        self,
        predictions: list[PredictionRecord],
        train_ratio: float = 0.8,
    ) -> HistoricalMLEvaluation:

        examples = self.dataset.build(
            predictions
        )

        skipped = (
            len(predictions)
            - len(examples)
        )

        if len(examples) < 2:
            return HistoricalMLEvaluation(
                prediction_count=len(predictions),
                training_examples=len(examples),
                skipped_predictions=skipped,
                evaluation=None,
            )

        evaluation = evaluate_baseline(
            examples,
            train_ratio=train_ratio,
        )

        return HistoricalMLEvaluation(
            prediction_count=len(predictions),
            training_examples=len(examples),
            skipped_predictions=skipped,
            evaluation=evaluation,
        )
