"""Read-only Binance market-universe scanner bridge for ATLAS."""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from atlas.adapters.binance_market_data import BinanceMarketData
from atlas.adapters.news import NewsAdapter
from atlas.market.market_scout import AssetType, MarketObservation
from atlas.services.scanner_service import ScannerResult, ScannerService
from atlas.trading.indicator_engine import IndicatorEngine


class BinanceScannerService:
    """Build scanner observations from Binance's public ticker and candle feeds."""

    DEFAULT_QUOTE_ASSETS = frozenset({"USDT", "USDC"})
    DEFAULT_MIN_QUOTE_VOLUME = 100_000.0
    DEFAULT_VOLUME_INTERVAL = "1h"
    DEFAULT_VOLUME_SAMPLES = 24
    DEFAULT_VOLUME_ENRICHMENT_LIMIT = 15
    DEFAULT_VOLUME_CACHE_TTL_SECONDS = 300.0
    DEFAULT_CATALYST_CACHE_TTL_SECONDS = 3600.0
    DEFAULT_ENRICHMENT_WORKERS = 8

    # Finnhub relationships are preferred, but crypto-news feeds are not
    # guaranteed to populate them. These aliases make catalyst matching
    # resilient when an article only mentions the asset in text.
    CRYPTO_NAME_ALIASES = {
        "BTC": ("bitcoin",),
        "ETH": ("ethereum",),
        "BNB": ("binance coin",),
        "SOL": ("solana",),
        "XRP": ("ripple",),
        "ADA": ("cardano",),
        "DOGE": ("dogecoin",),
        "AVAX": ("avalanche",),
        "DOT": ("polkadot",),
        "LINK": ("chainlink",),
        "TRX": ("tron",),
        "SUI": ("sui",),
        "TON": ("toncoin",),
        "LTC": ("litecoin",),
        "BCH": ("bitcoin cash",),
        "NEAR": ("near protocol",),
        "UNI": ("uniswap",),
        "ATOM": ("cosmos",),
        "XLM": ("stellar",),
        "ETC": ("ethereum classic",),
    }

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
        news_adapter=None,
        catalyst_cache_ttl_seconds: float = DEFAULT_CATALYST_CACHE_TTL_SECONDS,
    ) -> None:
        self.market_data = market_data
        self.scanner = scanner or ScannerService()
        self.quote_assets = quote_assets or self.DEFAULT_QUOTE_ASSETS
        self.min_quote_volume = min_quote_volume
        self.volume_interval = volume_interval
        self.volume_samples = max(1, volume_samples)
        self.volume_enrichment_limit = max(0, volume_enrichment_limit)
        self.volume_cache_ttl_seconds = max(0.0, volume_cache_ttl_seconds)
        self.news_adapter = news_adapter
        self.catalyst_cache_ttl_seconds = max(0.0, catalyst_cache_ttl_seconds)
        self._volume_cache: dict[
            str,
            tuple[float, float, float, float, float]
            | tuple[float, None, None, None, None],
        ] = {}
        self._relative_volume_5m_cache: dict[
            str,
            tuple[float, float | None],
        ] = {}
        self._catalyst_cache_at = 0.0
        self._catalyst_symbols: set[str] = set()

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
        eligible: list[tuple[str, float, float, float, float]] = []

        for ticker in tickers:
            symbol = str(ticker.get("symbol", "")).strip().upper()
            quote_asset = self._quote_asset(symbol)
            if quote_asset not in self.quote_assets:
                continue

            try:
                price = float(ticker.get("lastPrice", 0.0))
                quote_volume = float(ticker.get("quoteVolume", 0.0))
                change_percent = float(ticker.get("priceChangePercent", 0.0))
                high_price = float(ticker.get("highPrice", 0.0))
                low_price = float(ticker.get("lowPrice", 0.0))
            except (TypeError, ValueError):
                continue

            if price <= 0.0 or quote_volume < self.min_quote_volume:
                continue

            range_position = 0.0
            if high_price > low_price:
                range_position = min(
                    1.0,
                    max(0.0, (price - low_price) / (high_price - low_price)),
                )

            eligible.append(
                (symbol, price, quote_volume, change_percent, range_position)
            )

        enriched_symbols = self._select_volume_enrichment_symbols(eligible)
        catalyst_symbols = self._catalyst_symbols_for_universe(
            symbol for symbol, _, _, _, _ in eligible
        )
        volume_data = self._enrich_volume_data(enriched_symbols)
        relative_volume_5m = self._enrich_relative_volume_5m(enriched_symbols)
        observations: list[MarketObservation] = []
        for symbol, price, quote_volume, change_percent, _ in eligible:
            volume = quote_volume
            average_volume = quote_volume
            breakout_percent = 0.0
            atr_percent = 0.0
            enriched = volume_data.get(symbol)
            if enriched is not None:
                volume, average_volume, breakout_percent, atr_percent = enriched

            observations.append(
                MarketObservation(
                    symbol=symbol,
                    asset_type=AssetType.CRYPTO,
                    price=price,
                    volume=volume,
                    average_volume=average_volume,
                    change_percent=change_percent,
                    news_catalyst=symbol in catalyst_symbols,
                    breakout_percent=breakout_percent,
                    atr_percent=atr_percent,
                    relative_volume_5m=relative_volume_5m.get(symbol, 0.0),
                    liquid=True,
                )
            )
        return observations

    def _enrich_relative_volume_5m(
        self,
        symbols: set[str],
    ) -> dict[str, float]:
        """Fetch completed 5m relative quote-volume concurrently."""
        if not symbols:
            return {}

        workers = min(self.DEFAULT_ENRICHMENT_WORKERS, len(symbols))
        results: dict[str, float] = {}
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(self._relative_volume_5m, symbol): symbol
                for symbol in symbols
            }
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    relative_volume = future.result()
                except Exception:
                    continue
                if relative_volume is not None:
                    results[symbol] = relative_volume
        return results

    def _relative_volume_5m(self, symbol: str) -> float | None:
        """Compare the latest completed 5m quote-volume with its prior average."""
        now = time.monotonic()
        cached = self._relative_volume_5m_cache.get(symbol)
        if cached is not None:
            cached_at, relative_volume = cached
            if now - cached_at < self.volume_cache_ttl_seconds:
                return relative_volume

        try:
            klines = self.market_data.adapter.get_klines(
                symbol,
                interval="5m",
                limit=self.volume_samples + 1,
            )
        except Exception:
            self._relative_volume_5m_cache[symbol] = (now, None)
            return None

        candles = self._completed_market_candles(klines)
        if candles is None or len(candles) < self.volume_samples + 1:
            self._relative_volume_5m_cache[symbol] = (now, None)
            return None

        current = candles[-1][2]
        previous = candles[-(self.volume_samples + 1) : -1]
        average = sum(candle[2] for candle in previous) / len(previous)
        if current <= 0.0 or average <= 0.0:
            self._relative_volume_5m_cache[symbol] = (now, None)
            return None

        relative_volume = current / average
        self._relative_volume_5m_cache[symbol] = (now, relative_volume)
        return relative_volume

    def _enrich_volume_data(
        self,
        symbols: set[str],
    ) -> dict[str, tuple[float, float, float, float]]:
        """Fetch independent volume enrichments concurrently."""
        if not symbols:
            return {}

        workers = min(self.DEFAULT_ENRICHMENT_WORKERS, len(symbols))
        results: dict[str, tuple[float, float, float, float]] = {}
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(self._current_average_and_breakout, symbol): symbol
                for symbol in symbols
            }
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    enriched = future.result()
                except Exception:
                    continue
                if enriched is not None:
                    results[symbol] = enriched
        return results

    def _catalyst_symbols_for_universe(self, universe_symbols) -> set[str]:
        """Return Binance symbols supported by the current crypto-news feed.

        Finnhub's ``related`` field is the strongest signal. When it is absent,
        fall back to asset ticker/name mentions in headline + summary. Matching
        is limited to the current Binance universe.
        """
        now = time.monotonic()
        if (
            self._catalyst_cache_at > 0.0
            and now - self._catalyst_cache_at < self.catalyst_cache_ttl_seconds
        ):
            return set(self._catalyst_symbols)

        universe = {
            str(symbol).strip().upper()
            for symbol in universe_symbols
            if str(symbol).strip()
        }
        adapter = self.news_adapter
        if adapter is None:
            try:
                adapter = NewsAdapter()
            except Exception:
                self._catalyst_cache_at = now
                self._catalyst_symbols = set()
                return set()

        try:
            articles = adapter.latest_crypto_market_news()
        except Exception:
            articles = []

        symbols: set[str] = set()
        for article in articles:
            related = getattr(article, "related", ())
            for related_symbol in related:
                normalized = str(related_symbol).strip().upper()
                if not normalized:
                    continue
                if ":" in normalized:
                    normalized = normalized.rsplit(":", 1)[-1]
                if normalized.endswith(tuple(self.quote_assets)):
                    if normalized in universe:
                        symbols.add(normalized)
                    continue
                for quote_asset in self.quote_assets:
                    pair = f"{normalized}{quote_asset}"
                    if pair in universe:
                        symbols.add(pair)

            text = " ".join(
                str(getattr(article, field, "") or "")
                for field in ("title", "summary")
            ).lower()
            if not text:
                continue

            for symbol in universe:
                base = self._base_asset(symbol)
                aliases = self.CRYPTO_NAME_ALIASES.get(base, ())
                if self._contains_crypto_term(text, base) or any(
                    self._contains_crypto_term(text, alias)
                    for alias in aliases
                ):
                    symbols.add(symbol)

        self._catalyst_cache_at = now
        self._catalyst_symbols = symbols
        return set(symbols)

    @staticmethod
    def _contains_crypto_term(text: str, term: str) -> bool:
        """Match an asset/ticker as a standalone term, not a substring."""
        normalized = str(term).strip().lower()
        if not normalized:
            return False
        return re.search(
            rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])",
            text,
        ) is not None

    @staticmethod
    def _base_asset(symbol: str) -> str:
        normalized = str(symbol).strip().upper()
        for quote in ("USDT", "USDC"):
            if normalized.endswith(quote):
                return normalized[: -len(quote)]
        return normalized

    def _select_volume_enrichment_symbols(
        self,
        eligible: list[tuple[str, float, float, float, float]],
    ) -> set[str]:
        """Bound candle requests to the most relevant ticker candidates."""
        if self.volume_enrichment_limit == 0 or not eligible:
            return set()

        by_volume = sorted(eligible, key=lambda item: (-item[2], item[0]))
        by_momentum = sorted(eligible, key=lambda item: (-abs(item[3]), item[0]))
        by_range_position = sorted(
            eligible,
            key=lambda item: (-item[4], item[0]),
        )
        selected: set[str] = set()
        for item in by_volume[: self.volume_enrichment_limit]:
            selected.add(item[0])
        for item in by_momentum[: self.volume_enrichment_limit]:
            selected.add(item[0])
        for item in by_range_position[: self.volume_enrichment_limit]:
            selected.add(item[0])
        return selected

    def _current_average_and_breakout(self, symbol: str) -> tuple[float, float, float, float] | None:
        """Return current completed volume, prior average, and breakout pressure."""
        now = time.monotonic()
        cached = self._volume_cache.get(symbol)
        if cached is not None:
            cached_at, current, average, breakout, atr_percent = cached
            if now - cached_at < self.volume_cache_ttl_seconds:
                if current is None or average is None or breakout is None:
                    return None
                return current, average, breakout, atr_percent

        try:
            klines = self.market_data.adapter.get_klines(
                symbol,
                interval=self.volume_interval,
                limit=self.volume_samples + 1,
            )
        except Exception:
            self._volume_cache[symbol] = (now, None, None, None, None)
            return None

        candles = self._completed_market_candles(klines)
        if candles is None:
            volumes = self._parse_volume_candles(klines)
            if len(volumes) < self.volume_samples + 1:
                self._volume_cache[symbol] = (now, None, None, None, None)
                return None
            current = volumes[-1]
            previous = volumes[-(self.volume_samples + 1) : -1]
            average = sum(previous) / len(previous)
            breakout = 0.0
        else:
            if len(candles) < self.volume_samples + 1:
                self._volume_cache[symbol] = (now, None, None, None, None)
                return None
            current = candles[-1][2]
            previous = candles[-(self.volume_samples + 1) : -1]
            average = sum(candle[2] for candle in previous) / len(previous)
            previous_high = max(candle[0] for candle in previous)
            close = candles[-1][1]
            breakout = max(0.0, (close / previous_high - 1.0) * 100.0) if previous_high > 0 else 0.0

        if current <= 0.0 or average <= 0.0:
            self._volume_cache[symbol] = (now, None, None, None, None)
            return None

        breakout = round(max(0.0, breakout), 6)
        atr_percent = 0.0
        try:
            normalized = [
                BinanceMarketData._candle_from_kline(kline)
                for kline in klines
            ]
            indicators = IndicatorEngine().calculate(normalized)
            if indicators.atr_percent is not None:
                atr_percent = indicators.atr_percent
        except (TypeError, ValueError):
            pass

        self._volume_cache[symbol] = (
            now, current, average, breakout, atr_percent
        )
        return current, average, breakout, atr_percent

    @staticmethod
    def _parse_volume_candles(klines) -> list[float]:
        """Extract Binance quote-volume values from kline rows."""
        volumes: list[float] = []
        for kline in klines:
            try:
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
