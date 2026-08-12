from atlas.services.dashboard_data_service import DashboardDataService


def test_dashboard_exposes_active_trading_status():

    service = DashboardDataService()

    data = service.get_dashboard_data(
        selected_symbol="BTC-USD"
    )

    assert data["trading"]["mode"] == "advisor"
    assert data["trading"]["paper_trading"] is True
    assert data["trading"]["live_orders"] is False


def test_dashboard_status_reflects_selected_paper_mode():

    from atlas.services.settings_service import SettingsService

    service = SettingsService()
    service.set_trading_mode("paper")

    status = service.get_trading_status()

    assert status["mode"] == "paper"
    assert status["paper_trading"] is True
    assert status["live_orders"] is False


def test_dashboard_data_uses_settings_service_trading_mode():

    from atlas.services.dashboard_data_service import DashboardDataService

    service = DashboardDataService()

    service.settings.set_trading_mode("paper")

    dashboard = service.get_dashboard_data()

    assert dashboard["trading"]["mode"] == "paper"
    assert dashboard["trading"]["paper_trading"] is True
    assert dashboard["trading"]["live_orders"] is False

def test_dashboard_exposes_paper_trading_summary():

    from atlas.services.dashboard_data_service import DashboardDataService

    service = DashboardDataService()

    service.settings.set_trading_mode("paper")

    data = service.get_dashboard_data(
        selected_symbol="BTC-USD"
    )

    trading = data["trading"]

    assert "cash_nok" in trading
    assert "invested_nok" in trading
    assert "positions_value_nok" in trading
    assert "position_count" in trading
    assert "unrealized_pnl_nok" in trading
    assert "total_pnl_nok" in trading
    assert "return_percent" in trading
