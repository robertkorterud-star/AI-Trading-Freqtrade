from atlas.services.dashboard_data_service import DashboardDataService


def test_dashboard_reports_paper_trading_status():

    service = DashboardDataService()

    service.config.trading_mode = "paper"
    service.config.paper_trading = True

    data = service.get_dashboard_data(
        selected_symbol="BTC-USD"
    )

    assert data["status"] == "Running"
    assert data["trading"]["mode"] == "paper"
    assert data["trading"]["paper_trading"] is True
    assert data["trading"]["live_orders"] is False
    assert data["trading"]["virtual_capital_nok"] == 5000.0
