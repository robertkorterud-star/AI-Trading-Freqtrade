"""
ATLAS Prediction Tracker

Stores AI predictions for future outcome evaluation.
"""

from datetime import datetime

from atlas.models.decision_result import DecisionResult
from atlas.trading.prediction_record import PredictionRecord


class PredictionTracker:
    """Stores and manages AI predictions."""

    def __init__(self):
        self._predictions = []

    def record(
        self,
        decision: DecisionResult,
        price_usd: float,
        reason: str = "",
    ):
        prediction = PredictionRecord(
            symbol=decision.symbol,
            action=decision.action.value,
            confidence=decision.confidence,
            evidence=decision.evidence,
            price_usd=price_usd,
            timestamp=datetime.now(),
            analysts=list(decision.analysts),
            reason=reason,
        )

        self._predictions.append(prediction)

        return prediction

    def history(self):
        return [
            prediction.as_dict()
            for prediction in reversed(
                self._predictions
            )
        ]

    def count(self):
        return len(self._predictions)

    def clear(self):
        self._predictions.clear()
