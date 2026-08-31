"""
ATLAS Binance Market Data Adapter.

Read-only adapter for Binance public market data.
No API keys.
No order execution.

Converts Binance klines into ATLAS Candle / MarketSnapshot
contracts.
"""

from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from atlas.trading.market_data import Candle, MarketSnapshot


class BinanceMarketDataAdapter:
    """Fetches read-only OHLCV market data from Binance."""

    DEFAULT_BASE_URL = "https://api.binance.com"

    def __init__(
        self,
        base_url: str | None = None,
        opener=None,
        timeout: float = 5.0,
    ) -> None:
        self.base_url = (
            base_url.rstrip("/")
            if base_url
            else self.DEFAULT_BASE_URL
        )
        self._opener = opener or urlopen
        self.timeout = timeout

    def get_candles(
        self,
        symbol: str,
        interval: str = "1m",
        limit: int = 3,
    ) -> list[Candle]:
        """Fetch Binance klines and normalize them into ATLAS Candles."""

        if not symbol:
            raise ValueError("symbol must not be empty")

        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")

        params = urlencode(
            {
                "symbol": symbol.upper(),
                "interval": interval,
                "limit": limit,
            }
        )

        url = (
            f"{self.base_url}/api/v3/klines?{params}"
        )

        request = Request(
            url,
            headers={
                "User-Agent": "ATLAS-Trading-System/1.0",
                "Accept": "application/json",
            },
        )

        with self._opener(
            request,
            timeout=self.timeout,
        ) as response:
            payload = json.loads(
                response.read().decode("utf-8")
            )

        if not isinstance(payload, list):
            raise ValueError(
                "Binance klines response must be a list"
            )

        candles: list[Candle] = []

        for row in payload:
            if len(row) < 6:
                raise ValueError(
                    "invalid Binance kline row"
                )

            candles.append(
                Candle(
                    timestamp=float(row[0]) / 1000.0,
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
                )
            )

        if not candles:
            raise ValueError(
                f"Binance returned no candles for {symbol}"
            )

        return candles

    def get_snapshot(
        self,
        symbol: str,
        interval: str = "1m",
        limit: int = 3,
    ) -> MarketSnapshot:
        """Fetch Binance data and return an ATLAS MarketSnapshot."""

        candles = self.get_candles(
            symbol=symbol,
            interval=interval,
            limit=limit,
        )

        return MarketSnapshot.from_candles(
            symbol=symbol.upper(),
            candles=candles,
        )

    def get(
        self,
        symbol: str,
        interval: str = "1m",
        limit: int = 3,
    ) -> MarketSnapshot:
        """Compatibility alias for market-data adapters."""

        return self.get_snapshot(
            symbol=symbol,
            interval=interval,
            limit=limit,
        )
