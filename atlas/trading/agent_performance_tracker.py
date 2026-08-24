"""
ATLAS Agent Performance Tracker

Tracks how accurate each ATLAS analyst is over time.
"""

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AgentPerformance:
    """Performance statistics for one analyst."""

    analyst: str
    predictions: int = 0
    correct: int = 0

    @property
    def wrong(self):
        return self.predictions - self.correct

    @property
    def accuracy(self):
        if self.predictions == 0:
            return 0.0

        return round(
            self.correct
            / self.predictions
            * 100,
            2,
        )

    def as_dict(self):
        return {
            "analyst": self.analyst,
            "predictions": self.predictions,
            "correct": self.correct,
            "wrong": self.wrong,
            "accuracy": round(
                self.accuracy,
                2,
            ),
        }


class AgentPerformanceTracker:
    """Tracks prediction accuracy per analyst."""

    def __init__(
        self,
        storage_path: str | Path | None = None,
    ):
        self._performance = {}

        self.storage_path = (
            Path(storage_path)
            if storage_path is not None
            else None
        )

        if self.storage_path is not None:
            self._load()

    def _load(self):
        """Load performance data from JSON storage."""

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

        for analyst, values in data.items():

            if not analyst:
                continue

            self._performance[analyst] = AgentPerformance(
                analyst=analyst,
                predictions=int(
                    values.get("predictions", 0)
                ),
                correct=int(
                    values.get("correct", 0)
                ),
            )

    def _save(self):
        """Save performance data to JSON storage."""

        if self.storage_path is None:
            return

        self.storage_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = {
            analyst: {
                "predictions": performance.predictions,
                "correct": performance.correct,
            }
            for analyst, performance
            in self._performance.items()
        }

        serialized = json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )

        temporary_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.storage_path.parent,
                prefix=f".{self.storage_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(serialized)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            os.replace(
                temporary_path,
                self.storage_path,
            )
            temporary_path = None
        except Exception:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise

    def ensure(self, analyst: str):
        """Ensure an analyst exists without recording a prediction."""

        if not analyst:
            raise ValueError(
                "Analyst name must not be empty."
            )

        if analyst not in self._performance:
            self._performance[analyst] = AgentPerformance(
                analyst=analyst
            )

            self._save()

        return self._performance[analyst]

    def record(
        self,
        analyst: str,
        correct: bool,
    ):
        """Record one prediction result."""

        if not analyst:
            raise ValueError(
                "Analyst name must not be empty."
            )

        performance = self._performance.get(
            analyst
        )

        if performance is None:
            performance = AgentPerformance(
                analyst=analyst
            )

            self._performance[analyst] = (
                performance
            )

        performance.predictions += 1

        if correct:
            performance.correct += 1

        self._save()

        return performance

    def get(self, analyst: str):
        """Return performance for one analyst."""

        return self._performance.get(
            analyst
        )

    def history(self):
        """Return all analyst performance."""

        return [
            performance.as_dict()
            for performance in self._performance.values()
        ]

    def count(self):
        """Return number of tracked analysts."""

        return len(self._performance)

    def clear(self):
        """Clear all performance data."""

        self._performance.clear()
        self._save()
