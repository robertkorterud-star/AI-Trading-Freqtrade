from atlas.dashboard.app import app


def test_settings_route_exists():

    routes = {
        route.path
        for route in app.routes
    }

    assert "/settings" in routes
