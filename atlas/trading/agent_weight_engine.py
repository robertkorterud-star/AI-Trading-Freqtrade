"""
ATLAS Agent Weight Engine

Calculates adaptive weights for ATLAS analysts.

Weights are informational only.
They do not affect trading decisions yet.
"""

from atlas.trading.agent_performance_tracker import (
    AgentPerformanceTracker,
)


class AgentWeightEngine:
    """Calculates safe analyst weights from historical performance."""

    MIN_PREDICTIONS = 20
    MIN_WEIGHT = 0.10
    MAX_WEIGHT = 0.60

    def __init__(
        self,
        performance: AgentPerformanceTracker,
    ):
        self.performance = performance

    def calculate(self):
        """Return safe normalized weights for all analysts."""

        history = self.performance.history()

        if not history:
            return {}

        if any(
            item["predictions"] < self.MIN_PREDICTIONS
            for item in history
        ):
            equal_weight = 1.0 / len(history)

            return {
                item["analyst"]: round(equal_weight, 4)
                for item in history
            }

        scores = {
            item["analyst"]: max(
                0.0,
                float(item["accuracy"]),
            )
            for item in history
        }

        count = len(scores)

        if count == 0:
            return {}

        # Start everyone at the minimum.
        weights = {
            analyst: self.MIN_WEIGHT
            for analyst in scores
        }

        remaining = 1.0 - (
            self.MIN_WEIGHT * count
        )

        # Distribute the remaining weight according
        # to accuracy, while never exceeding MAX_WEIGHT.
        active = set(scores)

        while active and remaining > 1e-9:
            total_score = sum(
                scores[analyst]
                for analyst in active
            )

            if total_score <= 0:
                share = remaining / len(active)

                for analyst in active:
                    weights[analyst] += share

                remaining = 0.0
                break

            allocations = {
                analyst: (
                    remaining
                    * scores[analyst]
                    / total_score
                )
                for analyst in active
            }

            capped = False

            for analyst, allocation in allocations.items():
                available = (
                    self.MAX_WEIGHT
                    - weights[analyst]
                )

                if allocation > available:
                    weights[analyst] += available
                    remaining -= available
                    active.remove(analyst)
                    capped = True
                    break

            if capped:
                continue

            for analyst, allocation in allocations.items():
                weights[analyst] += allocation

            remaining = 0.0

        return {
            analyst: round(weight, 4)
            for analyst, weight in weights.items()
        }

