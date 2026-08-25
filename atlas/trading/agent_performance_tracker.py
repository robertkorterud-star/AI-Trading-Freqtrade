"""
ATLAS Agent Performance Tracker

Tracks how accurate each ATLAS analyst is over time.
"""

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class AgentPerformance:
    """Performance statistics for one analyst."""

    analyst: str
    predictions: int = 0
    correct: int = 0

    action_predictions: dict[str, int] = field(
        default_factory=dict
    )

    action_correct: dict[str, int] = field(
        default_factory=dict
    )

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

    @property
    def action_accuracy(self):
        actions = set(
            self.action_predictions
        ) | set(
            self.action_correct
        )

        return {
            action: round(
                self.action_correct.get(action, 0)
                / self.action_predictions[action]
                * 100,
                2,
            )
            for action in actions
            if self.action_predictions.get(action, 0) > 0
        }

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
            "action_predictions": dict(
                self.action_predictions
            ),
            "action_correct": dict(
                self.action_correct
            ),
            "action_accuracy": dict(
                self.action_accuracy
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
                action_predictions={
                    str(action): int(count)
                    for action, count in (
                        values.get(
                            "action_predictions",
                            {},
                        )
                    ).items()
                },
                action_correct={
                    str(action): int(count)
                    for action, count in (
                        values.get(
                            "action_correct",
                            {},
                        )
                    ).items()
                },
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
                "action_predictions": dict(
                    performance.action_predictions
                ),
                "action_correct": dict(
                    performance.action_correct
                ),
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
        action: str | None = None,
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

        if action:
            performance.action_predictions[action] = (
                performance.action_predictions.get(
                    action,
                    0,
                )
                + 1
            )

            if correct:
                performance.action_correct[action] = (
                    performance.action_correct.get(
                        action,
                        0,
                    )
                    + 1
                )

        self._save()

        return performance

    def rebuild_from_predictions(self, predictions):
        """Replace performance aggregates from evaluated predictions."""

        rebuilt = {}

        for prediction in predictions:
            if (
                not prediction.evaluated
                or prediction.correct is None
            ):
                continue

            for analyst in dict.fromkeys(prediction.analysts):
                if not analyst:
                    continue

                performance = rebuilt.get(analyst)

                if performance is None:
                    performance = AgentPerformance(
                        analyst=analyst
                    )
                    rebuilt[analyst] = performance

                performance.predictions += 1

                if prediction.correct:
                    performance.correct += 1

                action = prediction.action

                if action:
                    performance.action_predictions[action] = (
                        performance.action_predictions.get(
                            action,
                            0,
                        )
                        + 1
                    )

                    performance.action_correct[action] = (
                        performance.action_correct.get(
                            action,
                            0,
                        )
                    )

                    if prediction.correct:
                        performance.action_correct[action] += 1

        self._performance = rebuilt
        self._save()

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
