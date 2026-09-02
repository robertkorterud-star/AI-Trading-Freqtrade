"""
ATLAS Expected Return Model.

Provides a conservative baseline estimate of directional gross return
from observed historical outcomes. This model deliberately does not infer
return from confidence or evidence alone.
"""

from dataclasses import dataclass
from math import isfinite

from atlas.models.action import Action


@dataclass(frozen=True, slots=True)
class ExpectedReturnModel:
    """Estimate directional gross return from historical outcomes."""

    min_samples: int = 10
    haircut: float = 0.5
    max_return: float = 0.10

    def __post_init__(self) -> None:
        if self.min_samples < 1:
            raise ValueError("min_samples must be at least one")
        if not 0.0 < self.haircut <= 1.0:
            raise ValueError("haircut must be greater than zero and at most one")
        if self.max_return <= 0.0:
            raise ValueError("max_return must be greater than zero")

    def estimate(
        self,
        action: Action,
        historical_returns: list[float],
    ) -> float:
        """Return a conservative expected gross return as a decimal.

        Historical returns are expressed as decimal market returns, e.g.
        ``0.02`` for +2%. BUY uses returns in the normal direction while
        SELL reverses the direction. HOLD always returns zero.

        A positive estimate is returned only when enough historical samples
        exist and the directional historical mean is positive. The haircut
        keeps the baseline deliberately conservative and the cap prevents a
        small sample from producing an extreme estimate.
        """
        if action is Action.HOLD:
            return 0.0

        if len(historical_returns) < self.min_samples:
            return 0.0

        for value in historical_returns:
            if not isfinite(value):
                raise ValueError("historical_returns must contain finite values")

        direction = 1.0 if action is Action.BUY else -1.0
        directional_mean = (
            sum(value * direction for value in historical_returns)
            / len(historical_returns)
        )

        if directional_mean <= 0.0:
            return 0.0

        return min(
            directional_mean * self.haircut,
            self.max_return,
        )
