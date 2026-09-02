"""
ATLAS Historical Return Provider.

Provides evaluated historical directional returns to the expected return
model without exposing database details to the decision engine.
"""

from atlas.database.prediction_repository import PredictionRepository
from atlas.models.action import Action


class HistoricalReturnProvider:
    """Provide evaluated historical returns for a symbol and action."""

    def __init__(
        self,
        repository: PredictionRepository,
        max_samples: int = 100,
    ):
        if max_samples < 1:
            raise ValueError("max_samples must be at least one")

        self.repository = repository
        self.max_samples = max_samples

    def get_returns(
        self,
        symbol: str,
        action: Action,
    ) -> list[float]:
        """Return recent evaluated market returns for the requested action."""
        if action is Action.HOLD:
            return []

        predictions = self.repository.get_evaluated()

        returns = []

        for prediction in predictions:
            if prediction.symbol != symbol:
                continue

            if prediction.action != action.value:
                continue

            if prediction.price_change_percent is None:
                continue

            returns.append(
                prediction.price_change_percent / 100.0
            )

        return returns[-self.max_samples :]
