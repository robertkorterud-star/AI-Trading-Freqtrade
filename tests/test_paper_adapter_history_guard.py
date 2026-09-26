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

def test_new_trade_after_legacy_reset_survives_restart():
    from atlas.execution.models import ExecutionRequest
    from atlas.models.action import Action
    from atlas.trading.trading_service import TradingService

    class _Repository:
        def __init__(self, trades):
            self.trades = list(trades)

        def load(self):
            return list(self.trades)

        def save(self, trade):
            self.trades.append(trade)

    class _Exchange:
        def get_rate(self, base, target):
            return type("Rate", (), {"rate": 10.0})()

    class _AccountState:
        def __init__(self):
            self.replay_after = None

        def get_trade_replay_after(self):
            return self.replay_after

        def set_trade_replay_after(self, timestamp):
            self.replay_after = timestamp

    legacy_trade = TradeRecord(
        symbol="BTC-USD",
        action="BUY",
        quantity=0.2,
        price_usd=100_000.0,
        amount_nok=185_854.02,
        realized_pnl_nok=0.0,
        timestamp=datetime(2026, 9, 14, 7, 27, 24),
    )
    repository = _Repository([legacy_trade])
    account_state = _AccountState()

    first_portfolio = PortfolioService(starting_capital_nok=5_000.0)
    first_adapter = PaperTradingExecutionAdapter(
        portfolio=first_portfolio,
        trading=TradingService(repository=repository),
        exchange_service=_Exchange(),
        account_state_repository=account_state,
    )

    first_adapter.execute(
        ExecutionRequest(
            symbol="ETH-USD",
            action=Action.BUY,
            quantity=0.01,
            price=20_000.0,
        )
    )

    before_restart = first_portfolio.as_dict(10.0)
    assert any(
        position["symbol"] == "ETH-USD"
        for position in before_restart["positions"]
    )

    restarted_portfolio = PortfolioService(starting_capital_nok=5_000.0)
    PaperTradingExecutionAdapter(
        portfolio=restarted_portfolio,
        trading=TradingService(repository=repository),
        exchange_service=_Exchange(),
        account_state_repository=account_state,
    )

    after_restart = restarted_portfolio.as_dict(10.0)
    assert any(
        position["symbol"] == "ETH-USD"
        for position in after_restart["positions"]
    )

