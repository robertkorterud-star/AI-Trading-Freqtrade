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

    def calculate(
        self,
        action: str | None = None,
    ):
        """Return safe normalized weights for all analysts.

        When an action is supplied, calculate weights from the
        action-specific prediction history. Without an action,
        preserve the existing overall-performance behavior.
        """

        history = self.performance.history()

        if action is not None:
            normalized_action = str(action).upper()

            filtered_history = []

            for item in history:
                action_predictions = item.get(
                    "action_predictions",
                    {},
                )

                action_correct = item.get(
                    "action_correct",
                    {},
                )

                predictions = int(
                    action_predictions.get(
                        normalized_action,
                        0,
                    )
                )

                correct = int(
                    action_correct.get(
                        normalized_action,
                        0,
                    )
                )

                filtered_history.append(
                    {
                        **item,
                        "predictions": predictions,
                        "correct": correct,
                        "wrong": max(
                            predictions - correct,
                            0,
                        ),
                        "accuracy": (
                            round(
                                correct
                                / predictions
                                * 100,
                                2,
                            )
                            if predictions
                            else 0.0
                        ),
                    }
                )

            history = filtered_history

        if not history:
            return {}

        if any(
            item["predictions"] < self.MIN_PREDICTIONS
            for item in history
        ):
            equal_weight = 1.0 / len(history)

            rounded = {
                item["analyst"]: round(
                    equal_weight,
                    4,
                )
                for item in history
            }

            difference = round(
                1.0 - sum(rounded.values()),
                4,
            )

            if rounded and difference != 0.0:
                largest = next(
                    iter(rounded)
                )

                rounded[largest] = round(
                    rounded[largest] + difference,
                    4,
                )

            return rounded

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


    def explain(
        self,
        action: str | None = None,
    ):
        """Explain why each analyst currently has its weight.

        When an action is supplied, explain the action-specific
        learned weights using the same history used by calculate().
        Without an action, preserve the existing overall explanation.
        """

        history = self.performance.history()

        if action is not None:
            normalized_action = str(action).upper()

            filtered_history = []

            for item in history:
                action_predictions = item.get(
                    "action_predictions",
                    {},
                )

                action_correct = item.get(
                    "action_correct",
                    {},
                )

                predictions = int(
                    action_predictions.get(
                        normalized_action,
                        0,
                    )
                )

                correct = int(
                    action_correct.get(
                        normalized_action,
                        0,
                    )
                )

                filtered_history.append(
                    {
                        **item,
                        "predictions": predictions,
                        "correct": correct,
                        "wrong": max(
                            predictions - correct,
                            0,
                        ),
                        "accuracy": (
                            round(
                                correct
                                / predictions
                                * 100,
                                2,
                            )
                            if predictions
                            else 0.0
                        ),
                    }
                )

            history = filtered_history

        if not history:
            return {}

        weights = self.calculate(action=action)

        if any(
            item["predictions"] < self.MIN_PREDICTIONS
            for item in history
        ):
            return {
                item["analyst"]: {
                    "weight": weights.get(
                        item["analyst"],
                        0.0,
                    ),
                    "predictions": int(
                        item["predictions"]
                    ),
                    "accuracy": float(
                        item["accuracy"]
                    ),
                    "stabilized_accuracy": None,
                    "average_stabilized_accuracy": None,
                    "comparison": None,
                    "limit": None,
                    "status": "building_history",
                    "reason": (
                        "Building history. "
                        f"ATLAS requires at least "
                        f"{self.MIN_PREDICTIONS} predictions "
                        "before adaptive weighting begins."
                    ),
                }
                for item in history
            }

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

        average_score = (
            sum(scores.values())
            / len(scores)
        )

        explanations = {}

        for item in history:
            analyst = item["analyst"]
            score = scores[analyst]
            weight = weights.get(
                analyst,
                0.0,
            )

            predictions = int(
                item["predictions"]
            )

            accuracy = float(
                item["accuracy"]
            )

            if score > average_score:
                reason = (
                    "Higher weight because stabilized "
                    "historical performance is above "
                    "the analyst average."
                )
                comparison = "above_average"

            elif score < average_score:
                reason = (
                    "Lower weight because stabilized "
                    "historical performance is below "
                    "the analyst average."
                )
                comparison = "below_average"

            else:
                reason = (
                    "Weight reflects stabilized historical "
                    "performance close to the analyst average."
                )
                comparison = "average"

            if action is not None:
                reason += (
                    f" Action context: {str(action).upper()}."
                )

            if weight <= self.MIN_WEIGHT:
                reason += (
                    " The weight is constrained by "
                    "the minimum safety limit."
                )
                limit = "minimum"

            elif weight >= self.MAX_WEIGHT:
                reason += (
                    " The weight is constrained by "
                    "the maximum safety limit."
                )
                limit = "maximum"

            else:
                limit = None

            explanations[analyst] = {
                "weight": weight,
                "predictions": predictions,
                "accuracy": accuracy,
                "stabilized_accuracy": round(
                    score,
                    2,
                ),
                "average_stabilized_accuracy": round(
                    average_score,
                    2,
                ),
                "comparison": comparison,
                "limit": limit,
                "status": "adaptive",
                "reason": reason,
            }

        return explanations

