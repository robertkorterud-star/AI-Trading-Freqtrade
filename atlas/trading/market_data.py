"""
ATLAS Market Data Contracts.

Provides normalized market snapshots to the trading loop.
No exchange-specific implementation belongs here.
"""

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class Candle:
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self):
        if self.timestamp < 0:
            raise ValueError("timestamp must be non-negative")

        if self.open <= 0 or self.high <= 0:
            raise ValueError("prices must be greater than zero")

        if self.low <= 0 or self.close <= 0:
            raise ValueError("prices must be greater than zero")

        if self.high < self.low:
            raise ValueError("high must be greater than or equal to low")

        if self.volume < 0:
            raise ValueError("volume must be non-negative")


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    symbol: str
    timestamp: float
    price: float
    candles: tuple[Candle, ...]

    def __post_init__(self):
        if not self.symbol:
            raise ValueError("symbol must not be empty")

        if self.timestamp < 0:
            raise ValueError("timestamp must be non-negative")

        if self.price <= 0:
            raise ValueError("price must be greater than zero")

        if not isinstance(self.candles, tuple):
            raise TypeError("candles must be a tuple")

    @classmethod
    def from_candles(
        cls,
        symbol: str,
        candles: Sequence[Candle],
    ) -> "MarketSnapshot":
        if not candles:
            raise ValueError("at least one candle is required")

        latest = candles[-1]

        return cls(
            symbol=symbol,
            timestamp=latest.timestamp,
            price=latest.close,
            candles=tuple(candles),
        )
