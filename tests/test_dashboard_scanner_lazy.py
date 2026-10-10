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


def test_dashboard_injects_crypto_metadata_into_binance_scanner(tmp_path):
    config = AtlasConfig(database_path=str(tmp_path / "atlas.db"))
    crypto_metadata = object()

    service = DashboardService(
        config=config,
        binance_market_data=_FakeBinanceMarketData(),
        crypto_metadata=crypto_metadata,
    )

    assert service.binance_scanner.crypto_metadata is crypto_metadata


def test_dashboard_uses_coingecko_metadata_by_default(tmp_path):
    from atlas.adapters.coingecko import CoinGeckoAdapter

    config = AtlasConfig(database_path=str(tmp_path / "atlas.db"))
    service = DashboardService(
        config=config,
        binance_market_data=_FakeBinanceMarketData(),
    )

    assert isinstance(
        service.binance_scanner.crypto_metadata,
        CoinGeckoAdapter,
    )


def test_dashboard_wires_configured_binance_api_key_into_default_scanner(tmp_path):
    config = AtlasConfig(
        database_path=str(tmp_path / "atlas.db"),
        binance_api_key="test-binance-key",
    )

    service = DashboardService(config=config)

    assert service.binance_scanner.market_data.adapter.api_key == "test-binance-key"
