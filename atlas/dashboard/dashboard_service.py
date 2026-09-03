"""
Dashboard Service
"""

from atlas.services.dashboard_data_service import DashboardDataService
from atlas.services.scanner_service import ScannerService


class DashboardService:
    """Provides dashboard data."""

    def __init__(self):
        self.data = DashboardDataService()
        self.scanner = ScannerService()

    def get_dashboard(self, selected_symbol=None):
        dashboard = self.data.get_dashboard_data(selected_symbol=selected_symbol)
        scanner_result = self.scanner.scan([])
        dashboard["scanner"] = self.scanner.as_dict(scanner_result)
        return dashboard
