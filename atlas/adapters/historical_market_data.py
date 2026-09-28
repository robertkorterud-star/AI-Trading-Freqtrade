"""
Historical Market Data Adapter

Fetches historical OHLCV data for research and backtesting.

Uses the existing ATLAS historical contracts when available and keeps a
simple list[dict] API for compatibility.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

from atlas.trading.historical_data_provider import HistoricalDataProvider
from atlas.trading.historical_market_data import HistoricalMarketData, OHLCVBar


# Yahoo Finance constraints for intraday intervals.
_INTERVAL_MAX_PERIOD: dict[str, str] = {
    "1m": "7d",
    "2m": "60d",
    "5m": "60d",
    "15m": "60d",
    "30m": "60d",
    "60m": "730d",
    "90m": "60d",
    "1h": "730d",
    "1d": "max",
    "5d": "max",
    "1wk": "max",
    "1mo": "max",
    "3mo": "max",
}

_SUPPORTED_INTERVALS = frozenset(_INTERVAL_MAX_PERIOD)


class HistoricalMarketDataAdapter(HistoricalDataProvider):
    """Fetches historical market candles from Yahoo Finance.

    Implements ``HistoricalDataProvider.load()`` and keeps the legacy
    ``get()`` helper that returns plain dictionaries.
    """

    def __init__(
        self,
        *,
        interval: str = "1d",
        period: str = "1y",
        cache_dir: str | Path | None = None,
        auto_adjust: bool = False,
        source: str = "yfinance",
    ) -> None:
        normalized_interval = interval.strip().lower()
        if normalized_interval not in _SUPPORTED_INTERVALS:
            raise ValueError(
                f"Unsupported interval {interval!r}. "
                f"Supported: {sorted(_SUPPORTED_INTERVALS)}"
            )

        self.interval = normalized_interval
        self.period = period.strip()
        self.auto_adjust = bool(auto_adjust)
        self.source = source
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None

        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """Normalize common FX symbols to Yahoo Finance ticker symbols."""
        normalized = symbol.strip().upper()
        if not normalized:
            raise ValueError("symbol must not be empty.")

        fx_aliases = {
            "USDNOK=X": "NOK=X",
            "USDDKK=X": "DKK=X",
            "USDSEK=X": "SEK=X",
            "USDEUR=X": "EUR=X",
        }
        return fx_aliases.get(normalized, normalized)

    def load(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> HistoricalMarketData:
        """Load normalized historical OHLCV data for ``symbol``."""

        symbol = self._normalize_symbol(symbol)
        cache_key = self._cache_key(symbol, start, end)

        if self.cache_dir is not None:
            cached = self._read_cache(cache_key, symbol)
            if cached is not None:
                return cached

        history = self._download(symbol, start, end)
        bars = self._to_bars(history)

        data = HistoricalMarketData(
            symbol=symbol,
            bars=bars,
            timeframe=self.interval,
            source=self.source,
        )

        if self.cache_dir is not None:
            self._write_cache(cache_key, data)

        return data

    def get(
        self,
        symbol: str,
        period: str | None = None,
        interval: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[dict]:
        """Return historical candles as plain dictionaries (legacy API)."""

        previous_interval = self.interval
        previous_period = self.period

        try:
            if interval is not None:
                normalized = interval.strip().lower()
                if normalized not in _SUPPORTED_INTERVALS:
                    raise ValueError(
                        f"Unsupported interval {interval!r}. "
                        f"Supported: {sorted(_SUPPORTED_INTERVALS)}"
                    )
                self.interval = normalized

            if period is not None:
                self.period = period.strip()

            data = self.load(symbol, start=start, end=end)
        finally:
            self.interval = previous_interval
            self.period = previous_period

        return [
            {
                "timestamp": bar.timestamp.isoformat(),
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
            }
            for bar in data.bars
        ]

    def _download(
        self,
        symbol: str,
        start: datetime | None,
        end: datetime | None,
    ):
        ticker = yf.Ticker(symbol)

        if start is not None or end is not None:
            start_arg = start.strftime("%Y-%m-%d") if start is not None else None
            end_arg = end.strftime("%Y-%m-%d") if end is not None else None
            history = ticker.history(
                start=start_arg,
                end=end_arg,
                interval=self.interval,
                auto_adjust=self.auto_adjust,
            )
        else:
            history = ticker.history(
                period=self._safe_period(self.period),
                interval=self.interval,
                auto_adjust=self.auto_adjust,
            )

        if history is None or history.empty:
            raise ValueError(
                f"No historical data returned for {symbol} "
                f"(interval={self.interval})."
            )

        required = {"Open", "High", "Low", "Close"}
        missing = required - set(history.columns)
        if missing:
            raise ValueError(
                f"Yahoo Finance response for {symbol} is missing columns: "
                + ", ".join(sorted(missing))
            )

        return history.dropna(subset=["Open", "High", "Low", "Close"])

    def _safe_period(self, period: str) -> str:
        """Clamp period to Yahoo's limits for the selected interval."""

        max_period = _INTERVAL_MAX_PERIOD.get(self.interval)
        if max_period is None or max_period == "max":
            return period

        long_periods = {"6mo", "1y", "2y", "5y", "10y", "ytd", "max"}
        if period.lower() in long_periods:
            return max_period

        return period

    @staticmethod
    def _to_bars(history) -> list[OHLCVBar]:
        bars: list[OHLCVBar] = []

        for timestamp, row in history.iterrows():
            ts = timestamp.to_pydatetime()
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            else:
                ts = ts.astimezone(timezone.utc)

            volume = row["Volume"] if "Volume" in history.columns else 0.0
            if volume != volume:  # NaN
                volume = 0.0

            bars.append(
                OHLCVBar(
                    timestamp=ts,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(volume),
                )
            )

        return bars

    def _cache_key(
        self,
        symbol: str,
        start: datetime | None,
        end: datetime | None,
    ) -> str:
        start_part = start.isoformat() if start is not None else "none"
        end_part = end.isoformat() if end is not None else "none"
        raw = (
            f"{symbol}|{self.interval}|{self.period}|"
            f"{start_part}|{end_part}|{self.auto_adjust}"
        )
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]
        return f"{symbol.lower()}_{self.interval}_{digest}.json"

    def _cache_path(self, cache_key: str) -> Path:
        assert self.cache_dir is not None
        return self.cache_dir / cache_key

    def _read_cache(
        self,
        cache_key: str,
        symbol: str,
    ) -> HistoricalMarketData | None:
        path = self._cache_path(cache_key)
        if not path.exists():
            return None

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        try:
            bars = [
                OHLCVBar(
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
                for row in payload["bars"]
            ]
            return HistoricalMarketData(
                symbol=symbol,
                bars=bars,
                timeframe=payload.get("timeframe", self.interval),
                source=payload.get("source", self.source),
            )
        except (KeyError, TypeError, ValueError):
            return None

    def _write_cache(
        self,
        cache_key: str,
        data: HistoricalMarketData,
    ) -> None:
        path = self._cache_path(cache_key)
        payload = {
            "symbol": data.symbol,
            "timeframe": data.timeframe,
            "source": data.source,
            "bars": [
                {
                    "timestamp": bar.timestamp.isoformat(),
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                }
                for bar in data.bars
            ],
        }
        path.write_text(
            json.dumps(payload, separators=(",", ":")),
            encoding="utf-8",
        )
