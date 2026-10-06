"""Normalized historical derivatives market data for ATLAS.

These models contain descriptive market observations only.
They do not create trading actions or decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class FundingRateObservation:
    """Normalized historical funding-rate observation."""

    timestamp: datetime
    funding_rate: float
    mark_price: float

    def __post_init__(self):
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be datetime")

        if self.mark_price <= 0:
            raise ValueError("mark_price must be positive")


@dataclass(frozen=True, slots=True)
class OpenInterestObservation:
    """Normalized historical open-interest observation."""

    timestamp: datetime
    open_interest: float
    open_interest_value: float

    def __post_init__(self):
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be datetime")

        if self.open_interest < 0:
            raise ValueError("open_interest cannot be negative")

        if self.open_interest_value < 0:
            raise ValueError(
                "open_interest_value cannot be negative"
            )
