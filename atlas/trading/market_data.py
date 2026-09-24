"""
ATLAS Market Data Contracts.

Provides normalized market snapshots to the trading loop.
No exchange-specific implementation belongs here.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, Sequence


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

    def __getitem__(self, key: str) -> float:
        """Expose canonical OHLCV fields to mapping-style algorithms."""
        try:
            return getattr(self, key)
        except AttributeError as exc:
            raise KeyError(key) from exc

    def get(self, key: str, default=None):
        """Provide mapping-compatible field access without changing Candle ownership."""
        return getattr(self, key, default)


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    symbol: str
    timestamp: float
    price: float
    candles: tuple[Candle, ...]
    timeframe_candles: Mapping[str, tuple[Candle, ...]] = field(default_factory=dict)

    def __post_init__(self):
        if not self.symbol:
            raise ValueError("symbol must not be empty")
        if self.timestamp < 0:
            raise ValueError("timestamp must be non-negative")
        if self.price <= 0:
            raise ValueError("price must be greater than zero")
        if not isinstance(self.candles, tuple):
            raise TypeError("candles must be a tuple")
        normalized = {
            str(timeframe): tuple(candles)
            for timeframe, candles in self.timeframe_candles.items()
        }
        if any(not candles for candles in normalized.values()):
            raise ValueError("timeframe candles must not be empty")
        self._validate_chronology(self.candles)
        if self.candles and self.timestamp < self.candles[-1].timestamp:
            raise ValueError("snapshot timestamp must not be older than latest candle")
        for candles in normalized.values():
            self._validate_chronology(candles)
        object.__setattr__(self, "timeframe_candles", MappingProxyType(normalized))

    @staticmethod
    def _validate_chronology(candles: Sequence[Candle]) -> None:
        if any(
            current.timestamp <= previous.timestamp
            for previous, current in zip(candles, candles[1:])
        ):
            raise ValueError("candle timestamps must be strictly increasing")

    @classmethod
    def from_candles(
        cls,
        symbol: str,
        candles: Sequence[Candle],
        timeframe_candles: Mapping[str, Sequence[Candle]] | None = None,
    ) -> "MarketSnapshot":
        if not candles:
            raise ValueError("at least one candle is required")
        latest = candles[-1]
        normalized_timeframes = {
            timeframe: tuple(values)
            for timeframe, values in (timeframe_candles or {}).items()
        }
        return cls(
            symbol=symbol,
            timestamp=latest.timestamp,
            price=latest.close,
            candles=tuple(candles),
            timeframe_candles=normalized_timeframes,
        )
