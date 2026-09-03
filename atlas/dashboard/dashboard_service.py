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

    SCANNER_CACHE_TTL_SECONDS = 30.0

    def __init__(self, binance_market_data=None):
        self.data = DashboardDataService()
        self.scanner = ScannerService()
        self.binance_scanner = BinanceScannerService(
            binance_market_data or BinanceMarketDataAdapter(),
            scanner=self.scanner,
        )
        self._scanner_cache = None
        self._scanner_cache_at = 0.0

    def _get_scanner_result(self):
        """Return a short-lived scanner snapshot to avoid duplicate API work."""
        now = time.monotonic()
        if (
            self._scanner_cache is not None
            and now - self._scanner_cache_at < self.SCANNER_CACHE_TTL_SECONDS
        ):
            return self._scanner_cache

        try:
            result = self.binance_scanner.scan(limit=50)
        except Exception:
            # The dashboard remains available when Binance is temporarily
            # unreachable or returns an invalid public market response.
            result = ScannerResult(0, 0, tuple())

        self._scanner_cache = result
        self._scanner_cache_at = now
        return result

    def get_dashboard(self, selected_symbol=None):
        dashboard = self.data.get_dashboard_data(selected_symbol=selected_symbol)
        scanner_result = self._get_scanner_result()
        dashboard["scanner"] = self.scanner.as_dict(scanner_result)
        return dashboard
