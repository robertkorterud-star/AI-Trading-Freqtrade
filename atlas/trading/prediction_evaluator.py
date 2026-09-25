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
from atlas.database.outcome_repository import OutcomeRepository
from atlas.database.analysis_snapshot_repository import (
    AnalysisSnapshotRepository,
)
from atlas.database.prediction_repository import PredictionRepository


class PredictionEvaluator:
    """Evaluates predictions after a defined time horizon."""

    def __init__(
        self,
        predictions: PredictionTracker,
        outcomes: OutcomeTracker,
        agent_performance: AgentPerformanceTracker | None = None,
        outcome_repository: OutcomeRepository | None = None,
    ):
        self.predictions = predictions
        self.outcomes = outcomes
        self.agent_performance = (
            agent_performance
            or AgentPerformanceTracker()
        )

        self.outcome_repository = (
            outcome_repository
        )

        self.prediction_repository = None
        self.analysis_snapshot_repository = None

        if (
            self.predictions.repository is not None
            and self.predictions.database is not None
        ):
            self.prediction_repository = (
                PredictionRepository(
                    self.predictions.database
                )
            )
            self.analysis_snapshot_repository = (
                AnalysisSnapshotRepository(
                    self.predictions.database
                )
            )

        self._reconcile_agent_performance()

    def _reconcile_agent_performance(self):
        """Rebuild persistent performance from evaluated predictions."""

        if self.prediction_repository is None:
            return

        evaluated_predictions = (
            self.prediction_repository.get_evaluated()
        )

        if evaluated_predictions:
            self.agent_performance.rebuild_from_predictions(
                evaluated_predictions
            )

    def analysis_snapshot_for(self, prediction):
        """Return the original analysis snapshot for a prediction."""

        snapshot_id = getattr(
            prediction,
            "analysis_snapshot_id",
            None,
        )

        if (
            snapshot_id is None
            or self.analysis_snapshot_repository is None
        ):
            return None

        return self.analysis_snapshot_repository.get_by_id(
            snapshot_id
        )

    def ready_predictions(
        self,
        hours: int = 24,
        now: datetime | None = None,
    ):
        """Return predictions old enough to evaluate."""

        now = now or datetime.now()

        cutoff = now - timedelta(hours=hours)

        if self.prediction_repository is not None:
            predictions = self.prediction_repository.get_pending()
        else:
            predictions = self.predictions._predictions

        return [
            prediction
            for prediction in predictions
            if (
                not prediction.evaluated
                and prediction.timestamp <= cutoff
            )
        ]

    def evaluate(
        self,
        prediction,
        current_price_usd: float,
    ):
        """Evaluate one prediction against the current price."""

        if prediction.evaluated:
            return None

        outcome = self.outcomes.evaluate(
            prediction=prediction,
            current_price_usd=current_price_usd,
        )

        prediction.evaluated = True
        prediction.correct = outcome.correct
        prediction.evaluated_price_usd = current_price_usd
        prediction.evaluated_at = datetime.now()

        if prediction.price_usd:
            prediction.price_change_percent = (
                (
                    current_price_usd
                    - prediction.price_usd
                )
                / prediction.price_usd
                * 100
            )

        # Persist the evaluated prediction and its
        # outcome when a database repository is present.
        prediction_id = getattr(
            prediction,
            "database_id",
            None,
        )

        persisted_prediction = (
            prediction_id is not None
            and self.prediction_repository is not None
        )

        if prediction_id is not None:

            if (
                self.prediction_repository is not None
                and self.outcome_repository is not None
            ):
                with self.predictions.database.connect() as connection:
                    try:
                        self.prediction_repository.update(
                            prediction_id=prediction_id,
                            prediction=prediction,
                            connection=connection,
                        )
                        self.outcome_repository.save(
                            prediction_id=prediction_id,
                            outcome=outcome,
                            connection=connection,
                        )
                        connection.commit()
                    except Exception:
                        connection.rollback()
                        raise

            elif self.prediction_repository is not None:
                self.prediction_repository.update(
                    prediction_id=prediction_id,
                    prediction=prediction,
                )

            elif self.outcome_repository is not None:
                self.outcome_repository.save(
                    prediction_id=prediction_id,
                    outcome=outcome,
                )

        if persisted_prediction:
            self._reconcile_agent_performance()
        else:
            for analyst in prediction.analysts:
                self.agent_performance.record(
                    analyst=analyst,
                    correct=outcome.correct,
                    action=prediction.action,
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
