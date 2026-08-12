from atlas.services.settings_service import SettingsService


def test_settings_service_preserves_selected_trading_mode():

    service = SettingsService()

    service.set_trading_mode("paper")

    status = service.get_trading_status()

    assert status["mode"] == "paper"
    assert status["paper_trading"] is True
    assert status["live_orders"] is False
