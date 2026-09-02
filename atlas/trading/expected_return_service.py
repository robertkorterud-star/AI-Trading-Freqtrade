"""
ATLAS Expected Return Service.

Combines historical outcome retrieval with the conservative expected return
model while keeping persistence details outside the decision engine.
"""

from atlas.models.action import Action
from atlas.trading.expected_return_model import ExpectedReturnModel
from atlas.trading.historical_return_provider import HistoricalReturnProvider


class ExpectedReturnService:
    """Estimate expected return from evaluated historical outcomes."""

    def __init__(
        self,
        provider: HistoricalReturnProvider,
        model: ExpectedReturnModel | None = None,
    ):
        self.provider = provider
        self.model = model or ExpectedReturnModel()

    def estimate(
        self,
        symbol: str,
        action: Action,
    ) -> float:
        """Return the conservative expected gross return."""
        historical_returns = self.provider.get_returns(
            symbol=symbol,
            action=action,
        )

        return self.model.estimate(
            action=action,
            historical_returns=historical_returns,
        )
