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

    volume: float

    average_volume: float

    volume_ratio: float

    currency: str = "USD"

    currency: str = "USD"


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

        if "Volume" not in history.columns:

            # Volume is unavailable. Keep technical analysis
            # functional and treat volume as neutral.
            volume = 0.0
            average_volume = 0.0
            volume_ratio = 1.0

        else:

            volume_series = history["Volume"].dropna()

            if len(volume_series) < 20:
                # Some providers may return price history
                # without enough usable volume data.
                volume = 0.0
                average_volume = 0.0
                volume_ratio = 1.0

            else:

                volume = float(
                    volume_series.iloc[-1]
                )

                average_volume = float(
                    volume_series.tail(20).mean()
                )

                if average_volume <= 0:
                    volume_ratio = 1.0
                else:
                    volume_ratio = (
                        volume / average_volume
                    )

        info = ticker.fast_info

        price = float(info["lastPrice"])

        previous = float(info["previousClose"])

        currency = (
            getattr(
                ticker,
                "fast_info",
                {},
            ).get(
                "currency",
                None,
            )
            or getattr(
                ticker,
                "info",
                {},
            ).get(
                "currency",
                None,
            )
            or "USD"
        )

        currency = str(
            currency
        ).upper()

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
