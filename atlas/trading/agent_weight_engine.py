"""
ATLAS Agent Weight Engine

Calculates adaptive weights for ATLAS analysts.

Weights are adaptive and influence analyst evidence
aggregation in decision-making.
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

        # Stabilize accuracy before converting it into
        # adaptive weights. This prevents a small number
        # of new predictions from causing large changes.
        scores = {}

        for item in history:
            predictions = int(
                item["predictions"]
            )

            accuracy = max(
                0.0,
                min(
                    100.0,
                    float(item["accuracy"]),
                ),
            )

            # Shrink observed accuracy toward a neutral
            # 50% baseline until enough history exists.
            #
            # This makes early performance changes less
            # influential while preserving long-term learning.
            stabilized_accuracy = (
                (
                    accuracy * predictions
                )
                + (
                    50.0 * self.MIN_PREDICTIONS
                )
            ) / (
                predictions
                + self.MIN_PREDICTIONS
            )

            scores[item["analyst"]] = (
                stabilized_accuracy
            )

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

        # Round weights for stable output, then correct the
        # largest weight so the returned weights always sum
        # to exactly 1.0.
        rounded = {
            analyst: round(weight, 4)
            for analyst, weight in weights.items()
        }

        difference = round(
            1.0 - sum(rounded.values()),
            4,
        )

        if rounded and difference != 0.0:
            largest = max(
                rounded,
                key=rounded.get,
            )

            rounded[largest] = round(
                rounded[largest] + difference,
                4,
            )

        return rounded

