"""
Dashboard Service
"""

from atlas.adapters.binance_market_data import BinanceMarketDataAdapter
from atlas.services.binance_scanner_service import BinanceScannerService
from atlas.services.dashboard_data_service import DashboardDataService
from atlas.services.scanner_service import ScannerService


class DashboardService:
    """Provides dashboard data."""

    def __init__(self, binance_market_data=None):
        self.data = DashboardDataService()
        self.scanner = ScannerService()
        self.binance_scanner = BinanceScannerService(
            binance_market_data or BinanceMarketDataAdapter(),
            scanner=self.scanner,
        )

    def get_dashboard(self, selected_symbol=None):
        dashboard = self.data.get_dashboard_data(selected_symbol=selected_symbol)
        try:
            scanner_result = self.binance_scanner.scan(limit=50)
        except Exception:
            # The dashboard remains available when Binance is temporarily
            # unreachable or returns an invalid public market response.
            scanner_result = ScannerResult(0, 0, tuple())
        dashboard["scanner"] = self.scanner.as_dict(scanner_result)
        return dashboard


# Keep the import local to the service contract while avoiding a second
# scanner implementation in the dashboard layer.
from atlas.services.scanner_service import ScannerResult
