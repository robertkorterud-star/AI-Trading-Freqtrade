"""Read-only Binance market-universe scanner bridge for ATLAS."""

from __future__ import annotations

from atlas.market.market_scout import AssetType, MarketObservation
from atlas.services.scanner_service import ScannerResult, ScannerService


class BinanceScannerService:
    """Build scanner observations from Binance's public 24h ticker feed."""

    DEFAULT_QUOTE_ASSETS = frozenset({"USDT", "USDC"})
    DEFAULT_MIN_QUOTE_VOLUME = 100_000.0

    def __init__(
        self,
        market_data,
        scanner: ScannerService | None = None,
        quote_assets: frozenset[str] | None = None,
        min_quote_volume: float = DEFAULT_MIN_QUOTE_VOLUME,
    ) -> None:
        self.market_data = market_data
        self.scanner = scanner or ScannerService()
        self.quote_assets = quote_assets or self.DEFAULT_QUOTE_ASSETS
        self.min_quote_volume = min_quote_volume

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
        observations: list[MarketObservation] = []
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

            observations.append(
                MarketObservation(
                    symbol=symbol,
                    asset_type=AssetType.CRYPTO,
                    price=price,
                    volume=quote_volume,
                    # The public 24h ticker does not provide a historical
                    # average-volume baseline. Keep the baseline neutral
                    # rather than pretending current volume is historical data.
                    average_volume=quote_volume,
                    change_percent=change_percent,
                    liquid=True,
                )
            )
        return observations

    @staticmethod
    def _quote_asset(symbol: str) -> str:
        for quote in ("USDT", "USDC"):
            if symbol.endswith(quote):
                return quote
        return ""
