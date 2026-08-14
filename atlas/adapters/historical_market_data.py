"""
Historical Market Data Adapter

Fetches historical OHLCV data for backtesting.
"""

import yfinance as yf


class HistoricalMarketDataAdapter:
    """Fetches historical market candles."""

    def get(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1h",
    ) -> list[dict]:
        """Return historical candles."""

        history = yf.Ticker(symbol).history(
            period=period,
            interval=interval,
        )

        candles = []

        for timestamp, row in history.iterrows():

            candles.append(
                {
                    "timestamp": str(timestamp),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": float(row["Volume"]),
                }
            )

        return candles
