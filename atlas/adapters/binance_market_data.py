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
        timeframes: tuple[str, ...] = (),
    ) -> MarketSnapshot:
        """Fetch primary and optional multi-timeframe Binance klines."""
        raw_klines = self.adapter.get_klines(
            symbol=symbol,
            interval=interval,
            limit=limit,
        )
        candles = tuple(self._candle_from_kline(kline) for kline in raw_klines)

        timeframe_candles = {}
        for timeframe in timeframes:
            if timeframe == interval:
                timeframe_candles[timeframe] = candles
                continue
            raw_timeframe = self.adapter.get_klines(
                symbol=symbol,
                interval=timeframe,
                limit=limit,
            )
            timeframe_candles[timeframe] = tuple(
                self._candle_from_kline(kline)
                for kline in raw_timeframe
            )

        return MarketSnapshot.from_candles(
            symbol=symbol,
            candles=candles,
            timeframe_candles=timeframe_candles,
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


class BinanceMarketDataAdapter(BinanceMarketData):
    """Backward-compatible Binance market-data adapter."""

    def __init__(self, adapter=None):
        if adapter is None:
            from atlas.adapters.binance import BinanceAdapter
            adapter = BinanceAdapter()
        super().__init__(adapter)

    def get_candles(
        self,
        symbol: str,
        interval: str = "1m",
        limit: int = 100,
    ) -> list[Candle]:
        """Return normalized ATLAS candles."""
        raw_klines = self.adapter.get_klines(
            symbol=symbol,
            interval=interval,
            limit=limit,
        )
        return [self._candle_from_kline(kline) for kline in raw_klines]

    def get_snapshot(
        self,
        symbol: str,
        interval: str = "1m",
        limit: int = 100,
        timeframes: tuple[str, ...] = (),
    ) -> MarketSnapshot:
        """Return a normalized ATLAS market snapshot."""
        return self.snapshot(symbol, interval, limit, timeframes)

    def get(
        self,
        symbol: str,
        interval: str = "1m",
        limit: int = 100,
    ) -> MarketSnapshot:
        """Compatibility alias for market-data consumers."""
        return self.get_snapshot(symbol, interval, limit)
