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
    ) -> "MarketSnapshot":
        """Return normalized ATLAS market data as a MarketSnapshot."""
        from atlas.trading.market_data import Candle, MarketSnapshot

        ticker = yf.Ticker(symbol)
        history = ticker.history(
            period=self.history_period,
            interval=interval,
        ).dropna(subset=["Open", "High", "Low", "Close"])

        if history.empty:
            raise ValueError(f"No market history available for {symbol}")

        history = history.tail(limit)

        candles = []
        for timestamp, row in history.iterrows():
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
        candles = tuple(candles)

        return MarketSnapshot.from_candles(
            symbol=symbol,
            candles=candles,
        )


class MarketDataAdapter:
    """Compatibility facade with dependency injection for future providers."""

    def __init__(self, provider: MarketDataProvider | None = None) -> None:
        self.provider = provider or YFinanceMarketDataProvider()

    def get(self, symbol: str) -> MarketData:
        return self.provider.get(symbol)
