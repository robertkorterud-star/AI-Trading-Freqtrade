"""Normalized OHLCV candle model used by ATLAS time-series intelligence."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MarketCandle:
    """One normalized OHLCV observation."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self) -> None:
        if self.high < self.low:
            raise ValueError("high must be greater than or equal to low")
        if self.open < 0 or self.high < 0 or self.low < 0 or self.close < 0:
            raise ValueError("OHLC prices must be non-negative")
        if self.volume < 0:
            raise ValueError("volume must be non-negative")
