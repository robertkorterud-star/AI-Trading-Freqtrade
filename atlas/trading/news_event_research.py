"""Research-only measurement of market prices following published news."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from atlas.trading.historical_market_data import HistoricalMarketData


@dataclass(frozen=True, slots=True)
class NewsEventReturn:
    horizon: timedelta
    target_timestamp: datetime
    observed_timestamp: datetime | None
    return_percent: float | None


@dataclass(frozen=True, slots=True)
class NewsEventObservation:
    article: dict
    published_at: datetime
    entry_timestamp: datetime
    entry_price: float
    returns: tuple[NewsEventReturn, ...]


@dataclass(frozen=True, slots=True)
class NewsEventResearchResult:
    symbol: str
    timeframe: str
    source: str
    observations: tuple[NewsEventObservation, ...]


class NewsEventResearch:
    """Measure returns using the first available bar open at/after each target time.

    Bars must use opening timestamps, as Binance OHLCV bars do. Missing
    intervals are never silently converted into zero returns.
    """

    DEFAULT_HORIZONS = (
        timedelta(minutes=15),
        timedelta(hours=1),
        timedelta(days=1),
        timedelta(days=7),
    )

    def __init__(self, horizons: tuple[timedelta, ...] | None = None):
        self.horizons = self.DEFAULT_HORIZONS if horizons is None else tuple(horizons)
        if not self.horizons or any(h <= timedelta(0) for h in self.horizons):
            raise ValueError("horizons must contain positive durations")

    @staticmethod
    def _published_at(article: dict) -> datetime | None:
        value = article.get("published_at")
        try:
            if isinstance(value, datetime):
                stamp = value
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                stamp = datetime.fromtimestamp(value, tz=timezone.utc)
            elif isinstance(value, str):
                value = value.strip()
                if len(value) == 14 and value.isdigit():
                    stamp = datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
                else:
                    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            else:
                return None
            if stamp.tzinfo is None or stamp.utcoffset() is None:
                return None
            return stamp.astimezone(timezone.utc)
        except (ValueError, OverflowError, OSError, TypeError):
            return None

    def run(self, *, data: HistoricalMarketData, articles: list[dict]) -> NewsEventResearchResult:
        bars = data.bars
        if any(bar.timestamp.tzinfo is None or bar.timestamp.utcoffset() is None for bar in bars):
            raise ValueError("historical bars must have timezone-aware opening timestamps")
        times = [bar.timestamp.astimezone(timezone.utc) for bar in bars]
        measured = []
        for article in articles:
            published = self._published_at(article) if isinstance(article, dict) else None
            if published is None:
                continue
            entry_index = bisect_left(times, published)
            if entry_index >= len(bars):
                continue
            entry = bars[entry_index]
            outcomes = []
            for horizon in self.horizons:
                target = times[entry_index] + horizon
                index = bisect_left(times, target)
                if index == len(bars):
                    outcomes.append(NewsEventReturn(horizon, target, None, None))
                else:
                    outcomes.append(NewsEventReturn(
                        horizon, target, times[index],
                        (bars[index].open / entry.open - 1.0) * 100.0,
                    ))
            measured.append(NewsEventObservation(
                article=dict(article), published_at=published,
                entry_timestamp=times[entry_index], entry_price=entry.open,
                returns=tuple(outcomes),
            ))
        return NewsEventResearchResult(data.symbol, data.timeframe, data.source, tuple(measured))
