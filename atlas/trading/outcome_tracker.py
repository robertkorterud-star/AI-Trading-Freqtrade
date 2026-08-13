"""
ATLAS Outcome Tracker

Evaluates whether an AI prediction was correct
after the market has moved.
"""

from dataclasses import dataclass
from datetime import datetime

from atlas.trading.prediction_record import PredictionRecord


@dataclass(slots=True)
class OutcomeRecord:
    symbol: str
    action: str
    prediction_price_usd: float
    outcome_price_usd: float
    change_percent: float
    correct: bool
    timestamp: datetime

    def as_dict(self):
        return {
            "symbol": self.symbol,
            "action": self.action,
            "prediction_price_usd": round(
                self.prediction_price_usd,
                2,
            ),
            "outcome_price_usd": round(
                self.outcome_price_usd,
                2,
            ),
            "change_percent": round(
                self.change_percent,
                2,
            ),
            "correct": self.correct,
            "timestamp": self.timestamp.isoformat(
                timespec="seconds"
            ),
        }


class OutcomeTracker:
    """Evaluates and stores prediction outcomes."""

    def __init__(self):
        self._outcomes = []

    def evaluate(
        self,
        prediction: PredictionRecord,
        current_price_usd: float,
        threshold_percent: float = 1.0,
    ):
        prediction_price = float(
            prediction.price_usd
        )

        current_price = float(
            current_price_usd
        )

        if prediction_price <= 0:
            raise ValueError(
                "Prediction price must be greater than zero."
            )

        change_percent = (
            (current_price - prediction_price)
            / prediction_price
            * 100
        )

        if prediction.action == "BUY":
            correct = (
                change_percent >= threshold_percent
            )

        elif prediction.action == "SELL":
            correct = (
                change_percent <= -threshold_percent
            )

        elif prediction.action == "HOLD":
            correct = (
                abs(change_percent)
                < threshold_percent
            )

        else:
            raise ValueError(
                f"Unknown prediction action: "
                f"{prediction.action}"
            )

        outcome = OutcomeRecord(
            symbol=prediction.symbol,
            action=prediction.action,
            prediction_price_usd=prediction_price,
            outcome_price_usd=current_price,
            change_percent=change_percent,
            correct=correct,
            timestamp=datetime.now(),
        )

        self._outcomes.append(outcome)

        return outcome

    def history(self):
        return [
            outcome.as_dict()
            for outcome in reversed(
                self._outcomes
            )
        ]

    def count(self):
        return len(self._outcomes)

    def correct_count(self):
        return sum(
            1
            for outcome in self._outcomes
            if outcome.correct
        )

    def accuracy(self):
        if not self._outcomes:
            return 0.0

        return (
            self.correct_count()
            / len(self._outcomes)
            * 100
        )

    def clear(self):
        self._outcomes.clear()
