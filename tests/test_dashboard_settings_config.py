from atlas.core.config import AtlasConfig
from atlas.dashboard.dashboard_service import DashboardService
from atlas.services.settings_service import SettingsService


def test_dashboard_and_settings_share_trading_config():
    config = AtlasConfig()
    dashboard = DashboardService(config=config)
    settings = SettingsService(config=config)

    settings.set_trading_mode("paper")

    assert dashboard.data.config is config
    assert dashboard.data.config.trading_mode == "paper"
    assert dashboard.data.config.paper_trading is True
