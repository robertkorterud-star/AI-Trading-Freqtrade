"""
ATLAS Prediction Tracker

Stores AI predictions for future outcome evaluation.
"""

import json
from datetime import datetime
from pathlib import Path

from atlas.models.decision_result import DecisionResult
from atlas.trading.prediction_record import PredictionRecord


class PredictionTracker:
    """Stores and manages AI predictions."""

    def __init__(
        self,
        storage_path: str | Path | None = None,
    ):
        self._predictions = []
        self.storage_path = (
            Path(storage_path)
            if storage_path is not None
            else None
        )

        if self.storage_path is not None:
            self._load()

    def _load(self):
        """Load prediction history from JSON storage."""

        if not self.storage_path.exists():
            return

        try:
            data = json.loads(
                self.storage_path.read_text()
            )
        except (
            OSError,
            json.JSONDecodeError,
        ):
            return

        if not isinstance(data, list):
            return

        for values in data:
            try:
                prediction = PredictionRecord(
                    symbol=values["symbol"],
                    action=values["action"],
                    confidence=float(values["confidence"]),
                    evidence=float(values["evidence"]),
                    price_usd=float(values["price_usd"]),
                    timestamp=datetime.fromisoformat(
                        values["timestamp"]
                    ),
                    analysts=list(values.get("analysts", [])),
                    reason=values.get("reason", ""),
                    evaluated=bool(values.get("evaluated", False)),
                    correct=values.get("correct"),
                    evaluated_price_usd=(
                        float(values["evaluated_price_usd"])
                        if values.get("evaluated_price_usd") is not None
                        else None
                    ),
                    price_change_percent=(
                        float(values["price_change_percent"])
                        if values.get("price_change_percent") is not None
                        else None
                    ),
                    evaluated_at=(
                        datetime.fromisoformat(values["evaluated_at"])
                        if values.get("evaluated_at") is not None
                        else None
                    ),
                )
            except (
                KeyError,
                TypeError,
                ValueError,
            ):
                continue

            self._predictions.append(prediction)

    def save(self):
        """Persist the current prediction history."""

        self._save()

    def _save(self):
        """Save prediction history to JSON storage."""

        if self.storage_path is None:
            return

        self.storage_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = [
            prediction.as_dict()
            for prediction in self._predictions
        ]

        self.storage_path.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            )
        )

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
        self._save()

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
        self._save()
