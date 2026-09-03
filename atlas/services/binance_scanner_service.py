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
    DEFAULT_VOLUME_ENRICHMENT_LIMIT = 50
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
        self.volume_samples = volume_samples
        self.volume_enrichment_limit = max(0, volume_enrichment_limit)
        self.volume_cache_ttl_seconds = max(0.0, volume_cache_ttl_seconds)
        self._volume_cache: dict[str, tuple[float, float | None]] = {}

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
            average_volume = quote_volume
            if symbol in enriched_symbols:
                historical_average = self._historical_average_volume(symbol)
                if historical_average is not None and historical_average > 0.0:
                    average_volume = historical_average

            observations.append(
                MarketObservation(
                    symbol=symbol,
                    asset_type=AssetType.CRYPTO,
                    price=price,
                    volume=quote_volume,
                    # Fall back to current volume when historical enrichment
                    # is unavailable, preserving the neutral v1 behaviour.
                    average_volume=average_volume,
                    change_percent=change_percent,
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

    def _historical_average_volume(self, symbol: str) -> float | None:
        """Return a cached mean quote-volume baseline from recent hourly candles."""
        now = time.monotonic()
        cached = self._volume_cache.get(symbol)
        if cached is not None:
            cached_at, value = cached
            if now - cached_at < self.volume_cache_ttl_seconds:
                return value

        try:
            klines = self.market_data.adapter.get_klines(
                symbol,
                interval=self.volume_interval,
                limit=self.volume_samples,
            )
        except Exception:
            self._volume_cache[symbol] = (now, None)
            return None

        volumes: list[float] = []
        for kline in klines:
            try:
                # Binance kline index 7 is quote asset volume.
                volumes.append(float(kline[7]))
            except (IndexError, TypeError, ValueError):
                continue
        if not volumes:
            self._volume_cache[symbol] = (now, None)
            return None

        average = sum(volumes) / len(volumes)
        self._volume_cache[symbol] = (now, average)
        return average

    @staticmethod
    def _quote_asset(symbol: str) -> str:
        for quote in ("USDT", "USDC"):
            if symbol.endswith(quote):
                return quote
        return ""
