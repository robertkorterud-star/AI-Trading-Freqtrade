"""Market data provider boundary and Yahoo Finance implementation."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import yfinance as yf

from atlas.models.market_candle import MarketCandle


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


class MarketHistoryProvider(Protocol):
    """Interface for normalized historical market data."""

    def get_history(self, symbol: str, period: str = "3mo") -> list[MarketCandle]:
        """Return chronological OHLCV candles for ``symbol``."""
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

    def get_history(self, symbol: str, period: str = "3mo") -> list[MarketCandle]:
        """Return normalized OHLCV history without calculating indicators."""
        history = yf.Ticker(symbol).history(period=period)
        required = {"Open", "High", "Low", "Close", "Volume"}
        if not required.issubset(history.columns):
            missing = ", ".join(sorted(required - set(history.columns)))
            raise ValueError(f"Missing market history columns for {symbol}: {missing}")

        candles: list[MarketCandle] = []
        for timestamp, row in history.dropna(subset=list(required)).iterrows():
            if hasattr(timestamp, "to_pydatetime"):
                timestamp = timestamp.to_pydatetime()
            if not isinstance(timestamp, datetime):
                raise ValueError("Market history contains an invalid timestamp")
            candles.append(
                MarketCandle(
                    timestamp=timestamp,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row["Volume"]),
                )
            )
        return candles

    def get(self, symbol: str) -> MarketData:
        history = self.get_history(symbol, self.history_period)
        close = [candle.close for candle in history]

        if len(close) < 50:
            raise ValueError(
                f"Insufficient market history for {symbol}: "
                f"need at least 50 valid closes, got {len(close)}."
            )

        ma20 = sum(close[-20:]) / 20
        ma50 = sum(close[-50:]) / 50
        volumes = [candle.volume for candle in history]
        average_volume = sum(volumes[-20:]) / 20
        volume = volumes[-1]
        volume_ratio = volume / average_volume if average_volume > 0 else 1.0

        info = yf.Ticker(symbol).fast_info
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


class MarketDataAdapter:
    """Compatibility facade with dependency injection for future providers."""

    def __init__(self, provider: MarketDataProvider | None = None) -> None:
        self.provider = provider or YFinanceMarketDataProvider()

    def get(self, symbol: str) -> MarketData:
        return self.provider.get(symbol)
