import pytest

from atlas.core.config import AtlasConfig
from atlas.dashboard.dashboard_service import DashboardService


class _FakeBinanceMarketData:
    def get(self, symbol):
        raise AssertionError("scanner should not run in this unit test")


def _config(tmp_path):
    return AtlasConfig(
        database_path=str(tmp_path / "atlas.db"),
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
    )


def test_dashboard_syncs_trade_recorded_after_service_start(tmp_path):
    service = DashboardService(
        config=_config(tmp_path),
        binance_market_data=_FakeBinanceMarketData(),
    )

    service.data.trading.record_buy(
        symbol="MSFT",
        quantity=0.21217596933818203,
        price_usd=505.4100036621094,
        amount_nok=1000.0000000000001,
    )

    service._sync_portfolio_with_new_trades()

    snapshot = service.data.portfolio.as_dict(10.0)

    assert snapshot["cash_nok"] == pytest.approx(4000.0)
    assert len(snapshot["positions"]) == 1
    assert snapshot["positions"][0]["symbol"] == "MSFT"
    assert snapshot["positions"][0]["quantity"] == pytest.approx(0.21217596933818203)


def test_dashboard_restores_latest_valid_trade_after_legacy_history(tmp_path):
    service = DashboardService(
        config=_config(tmp_path),
        binance_market_data=_FakeBinanceMarketData(),
    )

    service.data.trading.record_buy(
        symbol="BTC-USD",
        quantity=0.2,
        price_usd=100000.0,
        amount_nok=185854.02,
    )
    service.data.trading.record_buy(
        symbol="MSFT",
        quantity=0.21217596933818203,
        price_usd=505.4100036621094,
        amount_nok=1000.0000000000001,
        analysis_snapshot_id=1400,
    )

    restarted = DashboardService(
        config=_config(tmp_path),
        binance_market_data=_FakeBinanceMarketData(),
    )

    snapshot = restarted.data.portfolio.as_dict(10.0)

    assert snapshot["cash_nok"] == pytest.approx(4000.0)
    assert snapshot["position_count"] == 1
    assert snapshot["positions"][0]["symbol"] == "MSFT"
    assert snapshot["positions"][0]["quantity"] == pytest.approx(0.21217596933818203)
