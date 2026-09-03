import asyncio
from types import SimpleNamespace

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


def test_binance_candle_api_serializes_atlas_candles(monkeypatch):
    from atlas.dashboard import app as dashboard_app

    candle = SimpleNamespace(
        timestamp=1_760_000_000.0,
        open=100.0,
        high=105.0,
        low=99.0,
        close=103.0,
        volume=1234.0,
    )
    monkeypatch.setattr(
        dashboard_app.binance_market_data,
        "get_candles",
        lambda symbol, interval, limit: [candle],
    )

    request = SimpleNamespace(
        query_params={"symbol": "BTCUSDT", "interval": "1h", "limit": "200"}
    )
    response = asyncio.run(dashboard_app.binance_candles_api(request))
    payload = response.body.decode()

    assert '"timestamp":1760000000.0' in payload
    assert '"open":100.0' in payload
    assert '"close":103.0' in payload


def test_market_candle_api_normalizes_iso_timestamps(monkeypatch):
    from atlas.dashboard import app as dashboard_app

    monkeypatch.setattr(
        dashboard_app.historical_market_data,
        "get",
        lambda symbol, period, interval: [
            {
                "timestamp": "2026-09-03T12:00:00+00:00",
                "open": 100.0,
                "high": 105.0,
                "low": 99.0,
                "close": 103.0,
                "volume": 1234.0,
            }
        ],
    )

    request = SimpleNamespace(
        query_params={"symbol": "NVDA", "period": "3m", "interval": "1h"}
    )
    response = asyncio.run(dashboard_app.market_candles_api(request))
    payload = response.body.decode()

    assert '"timestamp":1788436800.0' in payload
    assert '"close":103.0' in payload
