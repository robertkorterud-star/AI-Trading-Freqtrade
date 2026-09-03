from atlas.dashboard.app import app
from atlas.services.scanner_service import ScannerResult


def test_atlas_scanner_route_is_registered():
    routes = {route.path for route in app.routes}
    assert "/scanner" in routes


def test_atlas_scanner_dashboard_contains_scanner_snapshot(monkeypatch):
    from atlas.dashboard.app import service

    monkeypatch.setattr(
        service.binance_scanner,
        "scan",
        lambda limit=50: ScannerResult(0, 0, tuple()),
    )

    dashboard = service.get_dashboard()

    assert "scanner" in dashboard
    assert dashboard["scanner"]["scanned"] == 0
    assert dashboard["scanner"]["eligible"] == 0
    assert dashboard["scanner"]["candidates"] == []
