from atlas.dashboard.app import app


def test_atlas_scanner_route_is_registered():
    routes = {route.path for route in app.routes}
    assert "/scanner" in routes


def test_atlas_scanner_dashboard_contains_scanner_snapshot():
    from atlas.dashboard.app import service

    dashboard = service.get_dashboard()

    assert "scanner" in dashboard
    assert dashboard["scanner"]["scanned"] == 0
    assert dashboard["scanner"]["eligible"] == 0
    assert dashboard["scanner"]["candidates"] == []
