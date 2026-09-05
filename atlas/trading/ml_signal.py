"""
ATLAS ML prediction signal.

Wraps an already-fitted ML baseline as an algorithm-style signal
producer without making final trading decisions.
"""

from dataclasses import dataclass

from atlas.algorithms.base import AlgorithmSignal
from atlas.models.action import Action
from atlas.trading.ml_baseline import LogisticRegressionBaseline
from atlas.trading.prediction_training_dataset import (
    PredictionTrainingExample,
)


@dataclass(slots=True)
class MLPredictionSignal:
    """Produce a prediction signal from a fitted ML model."""

    model: LogisticRegressionBaseline
    algorithm: str = "ml_baseline"
    timeframe: str = "model"

    def predict(
        self,
        example: PredictionTrainingExample,
    ) -> AlgorithmSignal:
        probability = self.model.predict_probability(example)
        confidence = abs(probability - 0.5) * 2.0

        if probability >= 0.5:
            action = Action.BUY
        else:
            action = Action.SELL

        return AlgorithmSignal(
            symbol=example.symbol,
            algorithm=self.algorithm,
            timeframe=self.timeframe,
            action=action,
            confidence=confidence,
            score=probability,
            reasoning=[
                f"ML probability={probability:.4f}",
            ],
        )
