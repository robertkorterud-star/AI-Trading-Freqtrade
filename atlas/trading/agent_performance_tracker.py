"""
ATLAS Agent Performance Tracker

Tracks how accurate each ATLAS analyst is over time.
"""

from dataclasses import dataclass


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

    def __init__(self):
        self._performance = {}

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
