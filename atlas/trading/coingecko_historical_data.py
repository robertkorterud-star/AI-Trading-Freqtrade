"""
ATLAS CoinGecko historical market data provider.

Converts CoinGecko market data into ATLAS HistoricalMarketData.
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


class CoinGeckoHTTPClient(Protocol):
    """Minimal HTTP client contract."""

    def get_market_chart(
        self,
        coin_id: str,
        vs_currency: str,
        days: str,
    ) -> dict:
        ...


class CoinGeckoHistoricalDataProvider(
    HistoricalDataProvider
):
    """Convert CoinGecko market-chart data to ATLAS format."""

    def __init__(
        self,
        client: CoinGeckoHTTPClient,
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

        payload = self.client.get_market_chart(
            coin_id=coin_id,
            vs_currency=self.vs_currency,
            days=days,
        )

        prices = payload.get(
            "prices",
            [],
        )

        volumes = payload.get(
            "total_volumes",
            [],
        )

        bars = []

        volume_by_timestamp = {
            int(timestamp): float(volume)
            for timestamp, volume in volumes
        }

        for timestamp, price in prices:

            timestamp_ms = int(timestamp)

            close = float(price)

            volume = volume_by_timestamp.get(
                timestamp_ms,
                0.0,
            )

            bars.append(
                OHLCVBar(
                    timestamp=datetime.fromtimestamp(
                        timestamp_ms / 1000,
                        tz=timezone.utc,
                    ),
                    open=close,
                    high=close,
                    low=close,
                    close=close,
                    volume=volume,
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

        delta = end - start

        return str(
            max(
                1,
                delta.days,
            )
        )
