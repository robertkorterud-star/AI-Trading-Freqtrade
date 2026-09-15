from datetime import datetime

from atlas.execution.paper_adapter import PaperTradingExecutionAdapter
from atlas.services.portfolio_service import PortfolioService
from atlas.trading.trade_record import TradeRecord


class _TradingHistory:
    def __init__(self, trades):
        self._trades = trades

    def history(self):
        return list(self._trades)


def test_paper_adapter_ignores_overspent_legacy_history():
    trades = [
        TradeRecord(
            symbol="BTC-USD",
            action="BUY",
            quantity=0.2,
            price_usd=100_000.0,
            amount_nok=185_854.02,
            realized_pnl_nok=0.0,
            timestamp=datetime(2026, 9, 14, 7, 27, 24),
        )
    ]
    portfolio = PortfolioService(starting_capital_nok=5_000.0)

    PaperTradingExecutionAdapter(
        portfolio=portfolio,
        trading=_TradingHistory(trades),
        exchange_service=object(),
    )

    snapshot = portfolio.as_dict(1.0)
    assert snapshot["cash_nok"] == 5_000.0
    assert snapshot["positions"] == []
