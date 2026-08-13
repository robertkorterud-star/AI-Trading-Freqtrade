"""
ATLAS Prediction Evaluator

Finds predictions that are ready to be evaluated
and converts them into outcomes.
"""

from datetime import datetime, timedelta

from atlas.trading.agent_performance_tracker import (
    AgentPerformanceTracker,
)
from atlas.trading.outcome_tracker import OutcomeTracker
from atlas.trading.prediction_tracker import PredictionTracker


class PredictionEvaluator:
    """Evaluates predictions after a defined time horizon."""

    def __init__(
        self,
        predictions: PredictionTracker,
        outcomes: OutcomeTracker,
        agent_performance: AgentPerformanceTracker | None = None,
    ):
        self.predictions = predictions
        self.outcomes = outcomes
        self.agent_performance = (
            agent_performance
            or AgentPerformanceTracker()
        )

        self._evaluated_predictions = set()

    def ready_predictions(
        self,
        hours: int = 24,
        now: datetime | None = None,
    ):
        """Return predictions old enough to evaluate."""

        now = now or datetime.now()

        cutoff = now - timedelta(hours=hours)

        ready = []

        for prediction in self.predictions._predictions:
            if prediction.timestamp <= cutoff:
                ready.append(prediction)

        return ready

    def evaluate(
        self,
        prediction,
        current_price_usd: float,
    ):
        """Evaluate one prediction against the current price."""

        outcome = self.outcomes.evaluate(
            prediction=prediction,
            current_price_usd=current_price_usd,
        )

        for analyst in prediction.analysts:
            self.agent_performance.record(
                analyst=analyst,
                correct=outcome.correct,
            )

        self._evaluated_predictions.add(
            id(prediction)
        )

        return outcome

    def evaluate_ready(
        self,
        current_prices_usd: dict[str, float],
        hours: int = 24,
        now: datetime | None = None,
    ):
        """Evaluate all ready predictions once."""

        results = []

        for prediction in self.ready_predictions(
            hours=hours,
            now=now,
        ):
            if id(prediction) in self._evaluated_predictions:
                continue

            price = current_prices_usd.get(
                prediction.symbol
            )

            if price is None:
                continue

            outcome = self.evaluate(
                prediction=prediction,
                current_price_usd=price,
            )

            if outcome is not None:
                results.append(outcome)

        return results
