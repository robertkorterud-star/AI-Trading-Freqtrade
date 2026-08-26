"""
ATLAS Prediction Training Dataset.

Transforms evaluated PredictionRecord objects into
training examples without leaking future information
into the feature set.
"""

from dataclasses import dataclass

from atlas.trading.prediction_record import PredictionRecord


@dataclass(frozen=True, slots=True)
class PredictionTrainingExample:
    """One supervised learning example."""

    features: dict[str, float]
    outcome: float

    symbol: str
    action: str
    timestamp: object


class PredictionTrainingDataset:
    """Build supervised-learning examples from predictions."""

    def build(
        self,
        predictions: list[PredictionRecord],
    ) -> list[PredictionTrainingExample]:

        examples = []

        for prediction in predictions:

            if not prediction.evaluated:
                continue

            if prediction.correct is None:
                continue

            if not prediction.features:
                continue

            outcome = self._outcome(
                prediction
            )

            examples.append(
                PredictionTrainingExample(
                    features=dict(
                        prediction.features
                    ),
                    outcome=outcome,
                    symbol=prediction.symbol,
                    action=prediction.action,
                    timestamp=prediction.timestamp,
                )
            )

        return examples

    @staticmethod
    def _outcome(
        prediction: PredictionRecord,
    ) -> float:

        if prediction.correct:
            return 1.0

        return 0.0
