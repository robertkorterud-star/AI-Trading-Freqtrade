"""
ATLAS Prediction Tracker

Stores AI predictions through the ATLAS SQLite repository.
"""

from datetime import datetime
from pathlib import Path

from atlas.database.connection import Database
from atlas.database.prediction_repository import (
    PredictionRepository,
)
from atlas.database.schema import initialize_database
from atlas.models.decision_result import DecisionResult
from atlas.trading.prediction_record import PredictionRecord


class PredictionTracker:
    """Stores and manages AI predictions."""

    def __init__(
        self,
        storage_path: str | Path | None = None,
        database: Database | None = None,
    ):
        # A tracker without an explicitly supplied database
        # remains an isolated in-memory tracker.
        #
        # Production code can explicitly provide the SQLite
        # database through storage_path/database.
        self.database = database
        self.repository = None

        if database is not None:

            initialize_database(
                database
            )

            self.repository = (
                PredictionRepository(database)
            )

        elif storage_path is not None:

            self.database = Database(
                storage_path
            )

            initialize_database(
                self.database
            )

            self.repository = (
                PredictionRepository(
                    self.database
                )
            )

        self._predictions = []

        if self.repository is not None:
            self._predictions = (
                self.repository.get_all()
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
            analysis_snapshot_id=decision.analysis_snapshot_id,
            analysts=list(decision.analysts),
            reason=reason,
        )

        self._predictions.append(
            prediction
        )

        if self.repository is not None:
            self.repository.save(
                prediction
            )

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

        if self.repository is not None:
            self.repository.clear()
