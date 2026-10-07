"""ATLAS Binance historical market-data provider.

Loads read-only Binance Spot klines into the existing
HistoricalMarketData contract used by ATLAS backtesting.
Only fully closed candles are included.
"""

from __future__ import annotations

from datetime import datetime, timezone

from atlas.adapters.binance import BinanceAdapter
from atlas.trading.historical_data_provider import (
    HistoricalDataProvider,
)
from atlas.trading.historical_market_data import (
    HistoricalMarketData,
    OHLCVBar,
)


class BinanceHistoricalDataProvider(HistoricalDataProvider):
    """Load normalized historical OHLCV data from Binance Spot."""

    def __init__(
        self,
        adapter=None,
        interval: str = "4h",
        limit: int = 500,
        source: str = "binance",
        now=None,
    ):
        self.adapter = adapter or BinanceAdapter()
        self.interval = interval
        self.limit = limit
        self.source = source
        self._now = now or (
            lambda: datetime.now(timezone.utc)
        )

    def load(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> HistoricalMarketData:
        """Load fully closed Binance klines as historical data."""

        raw_klines = self.load_raw_klines(
            symbol,
            start=start,
            end=end,
        )

        now_ms = int(self._now().timestamp() * 1000)

        bars = []

        for kline in raw_klines:
            if len(kline) < 7:
                raise ValueError(
                    "Binance historical kline must contain "
                    "at least 7 fields"
                )

            close_time_ms = int(kline[6])

            if close_time_ms >= now_ms:
                continue

            bars.append(
                OHLCVBar(
                    timestamp=datetime.fromtimestamp(
                        float(kline[0]) / 1000.0,
                        tz=timezone.utc,
                    ),
                    open=float(kline[1]),
                    high=float(kline[2]),
                    low=float(kline[3]),
                    close=float(kline[4]),
                    volume=float(kline[5]),
                )
            )

        return HistoricalMarketData(
            symbol=symbol,
            bars=bars,
            timeframe=self.interval,
            source=self.source,
        )

    def load_raw_klines(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> tuple[list, ...]:
        """Load raw Binance klines using historical pagination."""

        start_time = (
            int(start.timestamp() * 1000)
            if start is not None
            else None
        )
        end_time = (
            int(end.timestamp() * 1000)
            if end is not None
            else None
        )

        if start_time is not None and end_time is not None:
            raw_klines = []
            next_start_time = start_time

            while next_start_time < end_time:
                page = self.adapter.get_klines(
                    symbol=symbol,
                    interval=self.interval,
                    limit=self.limit,
                    start_time=next_start_time,
                    end_time=end_time,
                )

                if not page:
                    break

                page_next_start_time = int(page[-1][6]) + 1

                if page_next_start_time <= next_start_time:
                    break

                raw_klines.extend(page)

                if len(page) < self.limit:
                    break

                next_start_time = page_next_start_time
        else:
            raw_klines = self.adapter.get_klines(
                symbol=symbol,
                interval=self.interval,
                limit=self.limit,
                start_time=start_time,
                end_time=end_time,
            )

        return tuple(raw_klines)
