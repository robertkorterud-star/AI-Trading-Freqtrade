from atlas.core.config import AtlasConfig
from atlas.dashboard.dashboard_service import DashboardService


class _FakeBinanceMarketData:
    pass


def test_dashboard_defers_scanner_until_snapshot_is_read(tmp_path, monkeypatch):
    config = AtlasConfig(database_path=str(tmp_path / "atlas.db"))
    service = DashboardService(config=config, binance_market_data=_FakeBinanceMarketData())
    service.data.get_dashboard_data = lambda **kwargs: {"market": []}

    calls = []

    def fake_get_scanner():
        calls.append("scanner")
        return {"candidates": []}

    monkeypatch.setattr(service, "get_scanner", fake_get_scanner)

    dashboard = service.get_dashboard()

    assert calls == []
    assert dashboard["scanner"]["candidates"] == []
    assert calls == ["scanner"]
