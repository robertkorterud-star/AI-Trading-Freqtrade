"""
Dashboard Service
"""

import time

from atlas.adapters.binance_market_data import BinanceMarketDataAdapter
from atlas.services.binance_scanner_service import BinanceScannerService
from atlas.services.dashboard_data_service import DashboardDataService
from atlas.services.scanner_service import ScannerResult, ScannerService


class DashboardService:
    """Provides dashboard data."""

    # Scanner market data is intentionally refreshed only once per hour.
    # The scanner page reads the cached snapshot and never triggers a fresh
    # Binance request simply because the page was opened/refreshed.
    SCANNER_CACHE_TTL_SECONDS = 3600.0

    @staticmethod
    def _normalize_dashboard_symbol(symbol):
        """Map Binance-native crypto symbols to the dashboard market symbol."""
        value = str(symbol or "").strip().upper()
        for quote_asset in ("USDT", "USDC"):
            if value.endswith(quote_asset) and len(value) > len(quote_asset):
                return f"{value[:-len(quote_asset)]}-USD"
        return value

    def __init__(self, config=None, binance_market_data=None):
        self.data = DashboardDataService(config=config)
        self.scanner = ScannerService()
        self.binance_scanner = BinanceScannerService(
            binance_market_data or BinanceMarketDataAdapter(),
            scanner=self.scanner,
        )
        self._scanner_cache = None
        self._scanner_cache_at = 0.0

    def _get_scanner_result(self):
        """Return the hourly scanner snapshot, refreshing it when stale."""
        now = time.monotonic()
        if (
            self._scanner_cache is not None
            and now - self._scanner_cache_at < self.SCANNER_CACHE_TTL_SECONDS
        ):
            return self._scanner_cache

        try:
            # Keep the full eligible universe so Scanner filters/search can
            # find symbols that are outside the default top-50 ranking.
            result = self.binance_scanner.scan(limit=1000)
        except Exception:
            # The dashboard remains available when Binance is temporarily
            # unreachable or returns an invalid public market response.
            result = ScannerResult(0, 0, tuple())

        self._scanner_cache = result
        self._scanner_cache_at = now
        return result

    def get_scanner(self):
        """Return the cached scanner snapshot without loading full dashboard data."""
        return self.scanner.as_dict(self._get_scanner_result())

    def get_dashboard(self, selected_symbol=None):
        normalized_symbol = self._normalize_dashboard_symbol(selected_symbol)
        dashboard = self.data.get_dashboard_data(selected_symbol=normalized_symbol)
        dashboard["scanner"] = self.get_scanner()
        return dashboard
