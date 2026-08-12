from atlas.dashboard.app import app


def test_settings_update_route_exists():

    routes = {
        (route.path, tuple(route.methods or []))
        for route in app.routes
        if hasattr(route, "methods")
    }

    assert any(
        path == "/settings"
        and "POST" in methods
        for path, methods in routes
    )


def test_settings_update_changes_trading_mode():

    from atlas.dashboard.app import settings_service

    settings_service.set_trading_mode("advisor")

    settings_service.set_trading_mode("paper")

    status = settings_service.get_trading_status()

    assert status["mode"] == "paper"
    assert status["paper_trading"] is True
    assert status["live_orders"] is False


def test_settings_post_can_select_paper_mode():

    from atlas.dashboard.app import update_settings, settings_service

    settings_service.set_trading_mode("advisor")

    class FakeRequest:
        async def form(self):
            return {"trading_mode": "paper"}

    import asyncio

    response = asyncio.run(
        update_settings(FakeRequest())
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/settings"

    status = settings_service.get_trading_status()

    assert status["mode"] == "paper"
    assert status["paper_trading"] is True
    assert status["live_orders"] is False
