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


def test_dashboard_data_uses_settings_service_trading_mode(monkeypatch):

    from atlas.services.dashboard_data_service import DashboardDataService

    from atlas.adapters.market_data import MarketData

    market_data = MarketData(
        symbol="NVDA",
        price=100.0,
        previous_close=99.0,
        change_percent=1.01,
        ma20=98.0,
        ma50=95.0,
        volume=1_000_000,
        average_volume=1_000_000,
        volume_ratio=1.0,
    )

    monkeypatch.setattr(
        "atlas.agents.technical_analyst.MarketDataAdapter",
        lambda: type(
            "FakeMarketDataAdapter",
            (),
            {
                "get": lambda self, symbol: MarketData(
                    symbol=symbol,
                    price=market_data.price,
                    previous_close=market_data.previous_close,
                    change_percent=market_data.change_percent,
                    ma20=market_data.ma20,
                    ma50=market_data.ma50,
                    volume=market_data.volume,
                    average_volume=market_data.average_volume,
                    volume_ratio=market_data.volume_ratio,
                )
            },
        )(),
    )

    monkeypatch.setattr(
        "atlas.services.technical_service.MarketDataAdapter",
        lambda: type(
            "FakeTechnicalMarketDataAdapter",
            (),
            {
                "get": lambda self, symbol: MarketData(
                    symbol=symbol,
                    price=market_data.price,
                    previous_close=market_data.previous_close,
                    change_percent=market_data.change_percent,
                    ma20=market_data.ma20,
                    ma50=market_data.ma50,
                    volume=market_data.volume,
                    average_volume=market_data.average_volume,
                    volume_ratio=market_data.volume_ratio,
                )
            },
        )(),
    )

    service = DashboardDataService()

    service.settings.set_trading_mode("paper")

    dashboard = service.get_dashboard_data()

    assert dashboard["trading"]["mode"] == "paper"
    assert dashboard["trading"]["paper_trading"] is True
    assert dashboard["trading"]["live_orders"] is False


def test_dashboard_exposes_paper_trading_summary(
    monkeypatch,
):

    from atlas.services.dashboard_data_service import (
        DashboardDataService,
    )

    from atlas.adapters.market_data import MarketData

    market_data = MarketData(
        symbol="BTC-USD",
        price=100_000.0,
        previous_close=99_000.0,
        change_percent=1.01,
        ma20=98_000.0,
        ma50=95_000.0,
        volume=1_000_000.0,
        average_volume=1_000_000.0,
        volume_ratio=1.0,
    )

    fake_adapter = lambda: type(
        "FakeMarketDataAdapter",
        (),
        {
            "get": lambda self, symbol: MarketData(
                symbol=symbol,
                price=market_data.price,
                previous_close=market_data.previous_close,
                change_percent=market_data.change_percent,
                ma20=market_data.ma20,
                ma50=market_data.ma50,
                volume=market_data.volume,
                average_volume=market_data.average_volume,
                volume_ratio=market_data.volume_ratio,
                currency=market_data.currency,
            )
        },
    )()

    fake_adapter_instance = fake_adapter()

    monkeypatch.setattr(
        "atlas.agents.technical_analyst.MarketDataAdapter",
        lambda: fake_adapter_instance,
    )

    monkeypatch.setattr(
        "atlas.services.technical_service.MarketDataAdapter",
        lambda: fake_adapter_instance,
    )

    service = DashboardDataService()

    service.settings.set_trading_mode("paper")

    data = service.get_dashboard_data(
        selected_symbol="BTC-USD"
    )

    portfolio = data["portfolio"]

    assert "cash_nok" in portfolio
    assert "invested_nok" in portfolio
    assert "positions_value_nok" in portfolio
    assert "position_count" in portfolio
    assert "unrealized_pnl_nok" in portfolio
    assert "total_pnl_nok" in portfolio
    assert "return_percent" in portfolio
