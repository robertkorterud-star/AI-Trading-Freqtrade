from atlas.core.config import AtlasConfig
from atlas.services.settings_service import SettingsService


def test_settings_service_preserves_selected_trading_mode():

    service = SettingsService()

    service.set_trading_mode("paper")

    status = service.get_trading_status()

    assert status["mode"] == "paper"
    assert status["paper_trading"] is True
    assert status["live_orders"] is False


def test_settings_service_persists_settings_when_enabled(tmp_path):

    database_path = str(tmp_path / "settings.db")
    config = AtlasConfig(
        database_path=database_path,
        load_persisted_settings=True,
    )

    first = SettingsService(config=config)
    first.set_trading_mode("paper")
    first.set_ai_provider("openai")

    second = SettingsService(
        config=AtlasConfig(
            database_path=database_path,
            load_persisted_settings=True,
        )
    )

    assert second.get_trading_status()["mode"] == "paper"
    assert second.get_trading_status()["paper_trading"] is True
    assert second.get_ai_provider() == "openai"
