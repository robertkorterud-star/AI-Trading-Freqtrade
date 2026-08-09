"""
Dashboard Service
"""

from atlas.services.dashboard_data_service import DashboardDataService


class DashboardService:
    """Provides dashboard data."""

    def __init__(self):

        self.data = DashboardDataService()

    def get_dashboard(self):

        return self.data.get_dashboard_data()