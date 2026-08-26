"""
ATLAS Historical Market Data.

Normalized OHLCV representation for research and backtesting.

This module does not fetch data from external providers.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class OHLCVBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class HistoricalMarketData:
    """Validated chronological OHLCV dataset."""

    def __init__(
        self,
        symbol: str,
        bars: list[OHLCVBar],
        timeframe: str = "unknown",
        source: str = "unknown",
    ):
        if not symbol:
            raise ValueError(
                "symbol must not be empty."
            )

        if not timeframe:
            raise ValueError(
                "timeframe must not be empty."
            )

        if not source:
            raise ValueError(
                "source must not be empty."
            )

        self.symbol = symbol
        self.timeframe = timeframe
        self.source = source
        self._bars = self._validate(
            bars
        )

    @property
    def start(self) -> datetime | None:
        if not self._bars:
            return None

        return self._bars[0].timestamp

    @property
    def end(self) -> datetime | None:
        if not self._bars:
            return None

        return self._bars[-1].timestamp

    @property
    def bars(self) -> tuple[OHLCVBar, ...]:
        return tuple(self._bars)

    @property
    def closes(self) -> list[float]:
        return [
            bar.close
            for bar in self._bars
        ]

    @property
    def timestamps(self) -> list[datetime]:
        return [
            bar.timestamp
            for bar in self._bars
        ]

    def __len__(self) -> int:
        return len(self._bars)

    def _validate(
        self,
        bars: list[OHLCVBar],
    ) -> list[OHLCVBar]:

        validated = list(bars)

        previous_timestamp = None

        for bar in validated:

            if not isinstance(
                bar.timestamp,
                datetime,
            ):
                raise ValueError(
                    "timestamp must be datetime."
                )

            if (
                previous_timestamp is not None
                and bar.timestamp
                <= previous_timestamp
            ):
                raise ValueError(
                    "Bars must be chronological."
                )

            if bar.open <= 0:
                raise ValueError(
                    "open must be positive."
                )

            if bar.high <= 0:
                raise ValueError(
                    "high must be positive."
                )

            if bar.low <= 0:
                raise ValueError(
                    "low must be positive."
                )

            if bar.close <= 0:
                raise ValueError(
                    "close must be positive."
                )

            if bar.volume < 0:
                raise ValueError(
                    "volume cannot be negative."
                )

            if bar.high < max(
                bar.open,
                bar.close,
            ):
                raise ValueError(
                    "high must be >= open and close."
                )

            if bar.low > min(
                bar.open,
                bar.close,
            ):
                raise ValueError(
                    "low must be <= open and close."
                )

            previous_timestamp = (
                bar.timestamp
            )

        return validated
