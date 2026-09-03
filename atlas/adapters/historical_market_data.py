"""
Historical Market Data Adapter

Fetches historical OHLCV data for backtesting.
"""

import yfinance as yf


class HistoricalMarketDataAdapter:
    """Fetches historical market candles."""

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """Normalize common FX symbols to Yahoo Finance ticker symbols."""
        normalized = symbol.strip().upper()
        fx_aliases = {
            "USDNOK=X": "NOK=X",
            "USDDKK=X": "DKK=X",
            "USDSEK=X": "SEK=X",
            "USDEUR=X": "EUR=X",
        }
        return fx_aliases.get(normalized, normalized)

    def get(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1h",
    ) -> list[dict]:
        """Return historical candles."""

        history = yf.Ticker(
            self._normalize_symbol(symbol)
        ).history(
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
