"""Read-only Binance market-universe scanner bridge for ATLAS."""

from __future__ import annotations

import time

from atlas.market.market_scout import AssetType, MarketObservation
from atlas.services.scanner_service import ScannerResult, ScannerService


class BinanceScannerService:
    """Build scanner observations from Binance's public ticker and candle feeds."""

    DEFAULT_QUOTE_ASSETS = frozenset({"USDT", "USDC"})
    DEFAULT_MIN_QUOTE_VOLUME = 100_000.0
    DEFAULT_VOLUME_INTERVAL = "1h"
    DEFAULT_VOLUME_SAMPLES = 24
    DEFAULT_VOLUME_ENRICHMENT_LIMIT = 25
    DEFAULT_VOLUME_CACHE_TTL_SECONDS = 300.0

    def __init__(
        self,
        market_data,
        scanner: ScannerService | None = None,
        quote_assets: frozenset[str] | None = None,
        min_quote_volume: float = DEFAULT_MIN_QUOTE_VOLUME,
        volume_interval: str = DEFAULT_VOLUME_INTERVAL,
        volume_samples: int = DEFAULT_VOLUME_SAMPLES,
        volume_enrichment_limit: int = DEFAULT_VOLUME_ENRICHMENT_LIMIT,
        volume_cache_ttl_seconds: float = DEFAULT_VOLUME_CACHE_TTL_SECONDS,
    ) -> None:
        self.market_data = market_data
        self.scanner = scanner or ScannerService()
        self.quote_assets = quote_assets or self.DEFAULT_QUOTE_ASSETS
        self.min_quote_volume = min_quote_volume
        self.volume_interval = volume_interval
        self.volume_samples = max(1, volume_samples)
        self.volume_enrichment_limit = max(0, volume_enrichment_limit)
        self.volume_cache_ttl_seconds = max(0.0, volume_cache_ttl_seconds)
        self._volume_cache: dict[str, tuple[float, float, float, float] | tuple[float, None, None, None]] = {}

    def scan(self, limit: int = 50) -> ScannerResult:
        """Fetch the public ticker universe and return ranked candidates."""
        observations = self.observations()
        result = self.scanner.scan(observations)
        if limit < 1:
            return ScannerResult(result.scanned, result.eligible, tuple())
        return ScannerResult(
            scanned=result.scanned,
            eligible=result.eligible,
            candidates=result.candidates[:limit],
        )

    def observations(self) -> list[MarketObservation]:
        """Convert eligible USDT/USDC tickers into scanner observations."""
        tickers = self.market_data.adapter.get_24hr_tickers()
        eligible: list[tuple[str, float, float, float]] = []

        for ticker in tickers:
            symbol = str(ticker.get("symbol", "")).strip().upper()
            quote_asset = self._quote_asset(symbol)
            if quote_asset not in self.quote_assets:
                continue

            try:
                price = float(ticker.get("lastPrice", 0.0))
                quote_volume = float(ticker.get("quoteVolume", 0.0))
                change_percent = float(ticker.get("priceChangePercent", 0.0))
            except (TypeError, ValueError):
                continue

            if price <= 0.0 or quote_volume < self.min_quote_volume:
                continue
            eligible.append((symbol, price, quote_volume, change_percent))

        enriched_symbols = self._select_volume_enrichment_symbols(eligible)
        observations: list[MarketObservation] = []
        for symbol, price, quote_volume, change_percent in eligible:
            volume = quote_volume
            average_volume = quote_volume
            breakout_percent = 0.0
            if symbol in enriched_symbols:
                volume_data = self._current_average_and_breakout(symbol)
                if volume_data is not None:
                    volume, average_volume, breakout_percent = volume_data

            observations.append(
                MarketObservation(
                    symbol=symbol,
                    asset_type=AssetType.CRYPTO,
                    price=price,
                    # For enriched symbols both sides are 1h quote-volume
                    # values, making relative volume dimensionally comparable.
                    volume=volume,
                    # Fall back to current 24h volume when candle enrichment
                    # is unavailable, preserving the neutral v1 behaviour.
                    average_volume=average_volume,
                    change_percent=change_percent,
                    breakout_percent=breakout_percent,
                    liquid=True,
                )
            )
        return observations

    def _select_volume_enrichment_symbols(
        self,
        eligible: list[tuple[str, float, float, float]],
    ) -> set[str]:
        """Bound candle requests to the most relevant ticker candidates."""
        if self.volume_enrichment_limit == 0 or not eligible:
            return set()

        by_volume = sorted(eligible, key=lambda item: (-item[2], item[0]))
        by_momentum = sorted(eligible, key=lambda item: (-abs(item[3]), item[0]))
        selected: set[str] = set()
        for item in by_volume[: self.volume_enrichment_limit]:
            selected.add(item[0])
        for item in by_momentum[: self.volume_enrichment_limit]:
            selected.add(item[0])
        return selected

    def _current_average_and_breakout(self, symbol: str) -> tuple[float, float, float] | None:
        """Return current completed volume, prior average, and breakout pressure."""
        now = time.monotonic()
        cached = self._volume_cache.get(symbol)
        if cached is not None:
            cached_at, current, average, breakout = cached
            if now - cached_at < self.volume_cache_ttl_seconds:
                if current is None or average is None or breakout is None:
                    return None
                return current, average, breakout

        try:
            # Request one extra candle so an in-progress latest candle can be
            # excluded while still retaining ``volume_samples`` prior candles.
            klines = self.market_data.adapter.get_klines(
                symbol,
                interval=self.volume_interval,
                limit=self.volume_samples + 1,
            )
        except Exception:
            self._volume_cache[symbol] = (now, None, None, None)
            return None

        candles = self._completed_market_candles(klines)
        if candles is None:
            # If the feed does not expose usable close timestamps, accept the
            # supplied candles as completed rather than dropping enrichment.
            volumes = self._parse_volume_candles(klines)
            if len(volumes) < self.volume_samples + 1:
                self._volume_cache[symbol] = (now, None, None, None)
                return None
            current = volumes[-1]
            previous = volumes[-(self.volume_samples + 1) : -1]
            average = sum(previous) / len(previous)
            breakout = 0.0
        else:
            if len(candles) < self.volume_samples + 1:
                self._volume_cache[symbol] = (now, None, None, None)
                return None
            current = candles[-1][2]
            previous = candles[-(self.volume_samples + 1) : -1]
            average = sum(candle[2] for candle in previous) / len(previous)
            previous_high = max(candle[0] for candle in previous)
            close = candles[-1][1]
            breakout = max(0.0, (close / previous_high - 1.0) * 100.0) if previous_high > 0 else 0.0

        if current <= 0.0 or average <= 0.0:
            self._volume_cache[symbol] = (now, None, None, None)
            return None

        breakout = max(0.0, breakout)
        self._volume_cache[symbol] = (now, current, average, breakout)
        return current, average, breakout

    @staticmethod
    def _parse_volume_candles(klines) -> list[float]:
        """Extract Binance quote-volume values from kline rows."""
        volumes: list[float] = []
        for kline in klines:
            try:
                # Binance kline index 7 is quote asset volume.
                volume = float(kline[7])
            except (IndexError, TypeError, ValueError):
                continue
            if volume > 0.0:
                volumes.append(volume)
        return volumes

    @classmethod
    def _completed_market_candles(cls, klines) -> list[tuple[float, float, float]] | None:
        """Extract completed candles as (high, close, quote volume)."""
        now_ms = time.time() * 1000.0
        completed: list[tuple[float, float, float]] = []
        timestamp_seen = False
        for kline in klines:
            try:
                high = float(kline[2])
                close = float(kline[4])
                close_time = float(kline[6])
                volume = float(kline[7])
            except (IndexError, TypeError, ValueError):
                continue
            timestamp_seen = True
            if close_time <= now_ms and high > 0.0 and close > 0.0 and volume > 0.0:
                completed.append((high, close, volume))
        if not timestamp_seen:
            return None
        return completed

    @staticmethod
    def _quote_asset(symbol: str) -> str:
        for quote in ("USDT", "USDC"):
            if symbol.endswith(quote):
                return quote
        return ""
