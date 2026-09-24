"""Market data provider boundary and Yahoo Finance implementation."""

from dataclasses import dataclass
from typing import Protocol

import yfinance as yf


@dataclass
class MarketData:
    symbol: str
    price: float
    previous_close: float
    change_percent: float
    ma20: float
    ma50: float
    volume: float
    average_volume: float
    volume_ratio: float
    currency: str = "USD"


class MarketDataProvider(Protocol):
    """Minimal interface used by ATLAS market consumers."""

    def get(self, symbol: str) -> MarketData:
        """Return the latest normalized market snapshot for ``symbol``."""
        ...

    def snapshot_for_horizon(
        self,
        symbol: str,
        horizon,
        limit: int = 100,
    ):
        """Fetch the normalized candle snapshot for an analysis horizon."""
        from atlas.market.trading_horizon import timeframes_for_horizon

        timeframes = timeframes_for_horizon(horizon)

        return self.snapshot(
            symbol,
            interval=timeframes[0],
            limit=limit,
            timeframes=timeframes[1:],
        )

    def get_many(self, symbols: list[str]) -> dict[str, MarketData]:
        """Return normalized market snapshots for multiple symbols."""
        ...


def oslo_symbol(symbol: str) -> str:
    """Return a Yahoo Finance symbol for an Oslo Børs ticker.

    ``TRMED`` becomes ``TRMED.OL`` while an already-qualified symbol is
    preserved. This helper is intentionally explicit so non-Oslo assets are
    not silently rewritten.
    """
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("symbol must not be empty")
    return normalized if "." in normalized else f"{normalized}.OL"


class YFinanceMarketDataProvider:
    """Market-data provider backed by yfinance/Yahoo Finance."""

    def __init__(self, history_period: str = "3mo") -> None:
        self.history_period = history_period

    def get(self, symbol: str) -> MarketData:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period=self.history_period)
        close = history["Close"].dropna()

        if len(close) < 50:
            raise ValueError(
                f"Insufficient market history for {symbol}: "
                f"need at least 50 valid closes, got {len(close)}."
            )

        ma20 = close.rolling(20).mean().iloc[-1]
        ma50 = close.rolling(50).mean().iloc[-1]

        if "Volume" not in history.columns:
            volume = average_volume = 0.0
            volume_ratio = 1.0
        else:
            volume_series = history["Volume"].dropna()
            if len(volume_series) < 20:
                volume = average_volume = 0.0
                volume_ratio = 1.0
            else:
                volume = float(volume_series.iloc[-1])
                average_volume = float(volume_series.tail(20).mean())
                volume_ratio = (
                    volume / average_volume if average_volume > 0 else 1.0
                )

        info = ticker.fast_info
        price = float(info["lastPrice"])
        previous = float(info["previousClose"])
        currency = str(info.get("currency") or "USD").upper()
        change = ((price - previous) / previous) * 100

        return MarketData(
            symbol=symbol,
            price=price,
            currency=currency,
            previous_close=previous,
            change_percent=change,
            ma20=float(ma20),
            ma50=float(ma50),
            volume=volume,
            average_volume=average_volume,
            volume_ratio=float(volume_ratio),
        )

    def get_many(self, symbols: list[str]) -> dict[str, MarketData]:
        """Return market data for multiple symbols using one Yahoo download."""
        normalized = [symbol for symbol in symbols if symbol]
        if not normalized:
            return {}
        if len(normalized) == 1:
            try:
                return {normalized[0]: self.get(normalized[0])}
            except Exception:
                return {}

        history = yf.download(
            normalized,
            period=self.history_period,
            auto_adjust=False,
            progress=False,
            threads=True,
        )
        if history.empty:
            return {}

        close_data = history["Close"]
        volume_data = history["Volume"] if "Volume" in history else None
        results = {}

        for symbol in normalized:
            try:
                close = close_data[symbol].dropna()
                if len(close) < 50:
                    continue

                ma20 = close.rolling(20).mean().iloc[-1]
                ma50 = close.rolling(50).mean().iloc[-1]

                if volume_data is None:
                    volume = average_volume = 0.0
                    volume_ratio = 1.0
                else:
                    volume_series = volume_data[symbol].dropna()
                    if len(volume_series) < 20:
                        volume = average_volume = 0.0
                        volume_ratio = 1.0
                    else:
                        volume = float(volume_series.iloc[-1])
                        average_volume = float(volume_series.tail(20).mean())
                        volume_ratio = (
                            volume / average_volume
                            if average_volume > 0
                            else 1.0
                        )

                ticker = yf.Ticker(symbol)
                info = ticker.fast_info
                price = float(info["lastPrice"])
                previous = float(info["previousClose"])
                currency = str(info.get("currency") or "USD").upper()
                change = ((price - previous) / previous) * 100

                results[symbol] = MarketData(
                    symbol=symbol,
                    price=price,
                    currency=currency,
                    previous_close=previous,
                    change_percent=change,
                    ma20=float(ma20),
                    ma50=float(ma50),
                    volume=volume,
                    average_volume=average_volume,
                    volume_ratio=float(volume_ratio),
                )
            except Exception:
                continue

        return results

    def snapshot(
        self,
        symbol: str,
        interval: str = "1d",
        limit: int = 100,
        timeframes: tuple[str, ...] = (),
    ) -> "MarketSnapshot":
        """Return normalized ATLAS market data as a MarketSnapshot."""
        from atlas.trading.market_data import Candle, MarketSnapshot

        ticker = yf.Ticker(symbol)

        def load_candles(timeframe: str) -> tuple[Candle, ...]:
            history = ticker.history(
                period=self.history_period,
                interval=timeframe,
            ).dropna(subset=["Open", "High", "Low", "Close"])

            if history.empty:
                if timeframe == interval:
                    raise ValueError(
                        f"No market history available for {symbol}"
                    )
                raise ValueError(
                    f"No {timeframe} market history available for {symbol}"
                )

            candles = []
            for timestamp, row in history.tail(limit).iterrows():
                volume = row.get("Volume", 0.0)
                if volume != volume:
                    volume = 0.0

                candles.append(
                    Candle(
                        timestamp=float(timestamp.timestamp()),
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=float(volume),
                    )
                )

            return tuple(candles)

        candles = load_candles(interval)
        timeframe_candles = {
            timeframe: (
                candles
                if timeframe == interval
                else load_candles(timeframe)
            )
            for timeframe in dict.fromkeys(timeframes)
        }

        return MarketSnapshot.from_candles(
            symbol=symbol,
            candles=candles,
            timeframe_candles=timeframe_candles,
        )


class MarketDataAdapter:
    """Compatibility facade with dependency injection for future providers."""

    def __init__(self, provider: MarketDataProvider | None = None) -> None:
        self.provider = provider or YFinanceMarketDataProvider()

    def get(self, symbol: str) -> MarketData:
        return self.provider.get(symbol)

    def snapshot(
        self,
        symbol: str,
        interval: str = "1d",
        limit: int = 100,
        timeframes: tuple[str, ...] = (),
    ):
        """Delegate normalized candle snapshots to the configured provider."""
        return self.provider.snapshot(
            symbol,
            interval=interval,
            limit=limit,
            timeframes=timeframes,
        )

    def get_many(self, symbols: list[str]) -> dict[str, MarketData]:
        """Return batch market data while preserving per-symbol fallback behavior."""
        normalized = [symbol for symbol in symbols if symbol]
        if not normalized:
            return {}

        provider_get_many = getattr(self.provider, "get_many", None)
        if callable(provider_get_many):
            try:
                results = dict(provider_get_many(normalized))
            except Exception:
                results = {}
        else:
            results = {}

        for symbol in normalized:
            if symbol in results:
                continue
            try:
                results[symbol] = self.provider.get(symbol)
            except Exception:
                continue

        return results
