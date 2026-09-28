"""
ATLAS Expected Return Service.

Combines historical outcome retrieval with the conservative expected return
model while keeping persistence details outside the decision engine.
"""

from dataclasses import dataclass

from atlas.models.action import Action
from atlas.trading.expected_return_model import ExpectedReturnModel
from atlas.trading.historical_return_provider import HistoricalReturnProvider


@dataclass(frozen=True, slots=True)
class ExpectedReturnEstimate:
    """Expected return value together with history availability."""

    value: float
    ready: bool


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
        return self.estimate_with_status(
            symbol=symbol,
            action=action,
        ).value

    def estimate_with_status(
        self,
        symbol: str,
        action: Action,
    ) -> ExpectedReturnEstimate:
        """Return expected gross return and whether history is sufficient."""
        historical_returns = self.provider.get_returns(
            symbol=symbol,
            action=action,
        )

        value = self.model.estimate(
            action=action,
            historical_returns=historical_returns,
        )

        ready = (
            action is Action.HOLD
            or len(historical_returns) >= self.model.min_samples
        )

        return ExpectedReturnEstimate(
            value=value,
            ready=ready,
        )
