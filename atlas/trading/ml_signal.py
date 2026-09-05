"""
ATLAS ML prediction signal.

Wraps an already-fitted ML baseline as an algorithm-style signal
producer without making final trading decisions.
"""

from dataclasses import dataclass

from atlas.models.algorithm_signal import AlgorithmSignal
from atlas.trading.ml_baseline import LogisticRegressionBaseline
from atlas.trading.prediction_training_dataset import (
    PredictionTrainingExample,
)


@dataclass(slots=True)
class MLPredictionSignal:
    """Produce a prediction signal from a fitted ML model."""

    model: LogisticRegressionBaseline
    algorithm: str = "ml_baseline"

    def predict(
        self,
        example: PredictionTrainingExample,
    ) -> AlgorithmSignal:
        probability = self.model.predict_probability(example)
        confidence = abs(probability - 0.5) * 2.0

        if probability >= 0.5:
            action = "BUY"
        else:
            action = "SELL"

        return AlgorithmSignal(
            symbol=example.symbol,
            algorithm=self.algorithm,
            action=action,
            confidence=confidence,
            score=probability,
            reasoning=(
                f"ML probability={probability:.4f}"
            ),
        )
