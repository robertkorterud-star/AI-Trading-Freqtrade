from atlas.services.settings_service import SettingsService


def test_settings_service_defaults_to_advisor():

    service = SettingsService()

    config = service.get_config()

    assert config.trading_mode == "advisor"
    assert config.paper_trading is True


def test_settings_service_can_enable_paper_mode():

    service = SettingsService()

    service.set_trading_mode("paper")

    config = service.get_config()

    assert config.trading_mode == "paper"
    assert config.paper_trading is True


def test_settings_service_rejects_live_mode():

    service = SettingsService()

    try:
        service.set_trading_mode("live")
    except ValueError:
        return

    raise AssertionError("Live trading mode must be rejected")


def test_settings_service_returns_trading_status():

    service = SettingsService()

    status = service.get_trading_status()

    assert status["mode"] == "advisor"
    assert status["paper_trading"] is True
    assert status["live_orders"] is False
