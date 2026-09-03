from atlas.dashboard.app import app


def test_atlas_scanner_route_is_registered():
    routes = {
        route.path
        for route in app.routes
    }

    assert "/scanner" in routes
