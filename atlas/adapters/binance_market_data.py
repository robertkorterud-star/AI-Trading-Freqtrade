"""ATLAS Binance market-data bridge.

Converts read-only Binance klines into the exchange-neutral
MarketSnapshot contract used by the ATLAS intelligence pipeline.
"""

from __future__ import annotations

from atlas.trading.market_data import Candle, MarketSnapshot


class BinanceMarketData:
    """Build MarketSnapshot instances from Binance public klines."""

    def __init__(self, adapter):
        self.adapter = adapter

    def snapshot(
        self,
        symbol: str,
        interval: str = "1m",
        limit: int = 100,
    ) -> MarketSnapshot:
        """Fetch klines and convert them to an ATLAS MarketSnapshot."""
        raw_klines = self.adapter.get_klines(
            symbol=symbol,
            interval=interval,
            limit=limit,
        )

        candles = tuple(
            self._candle_from_kline(kline)
            for kline in raw_klines
        )

        return MarketSnapshot.from_candles(
            symbol=symbol,
            candles=candles,
        )

    @staticmethod
    def _candle_from_kline(kline: list) -> Candle:
        if len(kline) < 6:
            raise ValueError("Binance kline must contain at least 6 fields")

        return Candle(
            timestamp=float(kline[0]) / 1000.0,
            open=float(kline[1]),
            high=float(kline[2]),
            low=float(kline[3]),
            close=float(kline[4]),
            volume=float(kline[5]),
        )
