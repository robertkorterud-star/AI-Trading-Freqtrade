import pytest

from atlas.core.config import AtlasConfig
from atlas.dashboard.dashboard_service import DashboardService


class _FakeBinanceMarketData:
    def get(self, symbol):
        raise AssertionError("scanner should not run in this unit test")


def test_dashboard_syncs_trade_recorded_after_service_start(tmp_path):
    config = AtlasConfig(
        database_path=str(tmp_path / "atlas.db"),
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
    )
    service = DashboardService(
        config=config,
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
