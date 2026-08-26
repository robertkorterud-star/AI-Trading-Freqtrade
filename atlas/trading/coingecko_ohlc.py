"""
ATLAS CoinGecko OHLC data provider.

Converts CoinGecko OHLC responses into normalized
HistoricalMarketData.
"""

from datetime import datetime, timezone
from typing import Protocol

from atlas.trading.historical_data_provider import (
    HistoricalDataProvider,
)
from atlas.trading.historical_market_data import (
    HistoricalMarketData,
    OHLCVBar,
)


class CoinGeckoOHLCClient(Protocol):

    def get_ohlc(
        self,
        coin_id: str,
        vs_currency: str,
        days: str,
    ) -> list[list[float]]:
        ...


class CoinGeckoOHLCProvider(
    HistoricalDataProvider
):
    """Load real OHLC candles from CoinGecko."""

    def __init__(
        self,
        client: CoinGeckoOHLCClient,
        coin_ids: dict[str, str] | None = None,
        vs_currency: str = "usd",
    ):
        self.client = client
        self.coin_ids = coin_ids or {}
        self.vs_currency = vs_currency

    def load(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> HistoricalMarketData:

        coin_id = self.coin_ids.get(
            symbol,
            symbol.lower(),
        )

        days = self._days(
            start,
            end,
        )

        rows = self.client.get_ohlc(
            coin_id=coin_id,
            vs_currency=self.vs_currency,
            days=days,
        )

        bars = []

        for row in rows:

            if len(row) < 5:
                raise ValueError(
                    "CoinGecko OHLC row must contain "
                    "timestamp, open, high, low and close."
                )

            timestamp_ms = int(row[0])

            bars.append(
                OHLCVBar(
                    timestamp=datetime.fromtimestamp(
                        timestamp_ms / 1000,
                        tz=timezone.utc,
                    ),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=0.0,
                )
            )

        return HistoricalMarketData(
            symbol=symbol,
            bars=bars,
        )

    @staticmethod
    def _days(
        start: datetime | None,
        end: datetime | None,
    ) -> str:

        if start is None or end is None:
            return "30"

        if end <= start:
            raise ValueError(
                "end must be after start."
            )

        return str(
            max(
                1,
                (end - start).days,
            )
        )
