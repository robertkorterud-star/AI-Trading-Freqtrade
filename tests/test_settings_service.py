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
    assert status["accumulation_drop_pct"] == 2.0


def test_settings_service_defaults_to_ollama_ai_provider():

    service = SettingsService()

    assert service.get_ai_provider() == "ollama"


def test_settings_service_can_set_ollama_ai_provider():

    service = SettingsService()

    service.set_ai_provider("ollama")

    assert service.get_ai_provider() == "ollama"


def test_settings_service_can_set_openai_ai_provider():

    service = SettingsService()

    service.set_ai_provider("ollama")
    service.set_ai_provider("openai")

    assert service.get_ai_provider() == "openai"


def test_settings_service_rejects_unknown_ai_provider():

    service = SettingsService()

    try:
        service.set_ai_provider("unknown")
    except ValueError:
        return

    raise AssertionError(
        "Unknown AI provider must be rejected"
    )


def test_settings_service_can_set_accumulation_drop_pct():

    service = SettingsService()

    service.set_accumulation_drop_pct(3.5)

    assert service.get_config().accumulation_drop_pct == 3.5
    assert service.get_trading_status()["accumulation_drop_pct"] == 3.5


def test_settings_service_rejects_invalid_accumulation_drop_pct():

    service = SettingsService()

    for value in (0.0, 20.1, "not-a-number"):
        try:
            service.set_accumulation_drop_pct(value)
        except ValueError:
            continue
        raise AssertionError(
            "Invalid accumulation_drop_pct must be rejected"
        )
