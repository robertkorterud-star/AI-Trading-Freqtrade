from atlas.dashboard.app import app


def test_settings_route_exists():

    routes = {
        route.path
        for route in app.routes
    }

    assert "/settings" in routes


def test_settings_route_supports_ai_provider():
    from atlas.dashboard.app import settings_service

    settings_service.set_ai_provider("openai")

    settings_service.set_ai_provider("ollama")

    assert settings_service.get_ai_provider() == "ollama"

    settings_service.set_ai_provider("openai")

    assert settings_service.get_ai_provider() == "openai"
