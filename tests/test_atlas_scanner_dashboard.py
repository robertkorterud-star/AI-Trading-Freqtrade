from atlas.dashboard.app import app
from atlas.services.scanner_service import ScannerResult


def test_atlas_scanner_route_is_registered():
    routes = {route.path for route in app.routes}
    assert "/scanner" in routes


def test_atlas_scanner_dashboard_contains_scanner_snapshot(monkeypatch):
    from atlas.dashboard.app import service

    service._scanner_cache = None
    service._scanner_cache_at = 0.0

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


def test_atlas_scanner_snapshot_is_cached_for_one_hour(monkeypatch):
    from atlas.dashboard.app import service

    service._scanner_cache = None
    service._scanner_cache_at = 0.0
    calls = {"count": 0}

    def fake_scan(limit=50):
        calls["count"] += 1
        return ScannerResult(10, 2, tuple())

    monkeypatch.setattr(service.binance_scanner, "scan", fake_scan)
    monkeypatch.setattr("atlas.dashboard.dashboard_service.time.monotonic", lambda: 100.0)

    first = service.get_scanner()
    second = service.get_scanner()

    assert first == second
    assert calls["count"] == 1


def test_atlas_scanner_route_does_not_load_full_dashboard(monkeypatch):
    import asyncio
    from atlas.dashboard import app as dashboard_app

    monkeypatch.setattr(
        dashboard_app.service,
        "get_scanner",
        lambda: {"scanned": 1, "eligible": 1, "candidates": []},
    )
    monkeypatch.setattr(
        dashboard_app.service,
        "get_dashboard",
        lambda: (_ for _ in ()).throw(AssertionError("full dashboard should not be loaded")),
    )

    response = asyncio.run(dashboard_app.scanner(None))

    assert response.template.name == "scanner.html"
    assert response.context["dashboard"]["scanner"]["scanned"] == 1
