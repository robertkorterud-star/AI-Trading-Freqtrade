"""
Market Data Adapter
"""

from dataclasses import dataclass

import yfinance as yf


@dataclass
class MarketData:

    symbol: str

    price: float

    previous_close: float

    change_percent: float

    ma20: float

    ma50: float


class MarketDataAdapter:
    """Fetches market data."""

    def get(self, symbol: str) -> MarketData:

        ticker = yf.Ticker(symbol)

        history = ticker.history(period="3mo")

        close = history["Close"].dropna()

        if len(close) < 50:
            raise ValueError(
                f"Insufficient market history for {symbol}: "
                f"need at least 50 valid closes, "
                f"got {len(close)}."
            )

        ma20 = close.rolling(20).mean().iloc[-1]

        ma50 = close.rolling(50).mean().iloc[-1]

        info = ticker.fast_info

        price = float(info["lastPrice"])

        previous = float(info["previousClose"])

        change = ((price - previous) / previous) * 100

        return MarketData(

            symbol=symbol,

            price=price,

            previous_close=previous,

            change_percent=change,

            ma20=float(ma20),

            ma50=float(ma50),

        )