from atlas.models.action import Action
from atlas.trading.dry_run_trader import DryRunTrader
from atlas.trading.paper_portfolio import PaperPortfolio
from atlas.trading.paper_portfolio_store import PaperPortfolioStore


def test_buy_persist_reload_sell_closes_position_and_realizes_pnl(tmp_path):
    path = tmp_path / "paper_portfolio.json"
    store = PaperPortfolioStore(path)
    portfolio = PaperPortfolio(initial_cash=5000.0)
    trader = DryRunTrader(
        portfolio=portfolio,
        max_position_value=5000.0,
    )

    buy = trader.process_signal(
        symbol="BTCUSDT",
        action=Action.BUY,
        price=100.0,
        confidence=0.90,
        risk_score=0.0,
        reason="deterministic lifecycle test entry",
    )

    assert buy.executed is True
    assert buy.action.value == "enter"
    assert buy.quantity > 0.0
    assert "BTCUSDT" in portfolio.positions
    assert trader.journal.trade_count == 1
    assert trader.journal.latest().action == "enter"

    store.save(portfolio)
    restored = store.load(initial_cash=5000.0)

    assert "BTCUSDT" in restored.positions
    assert restored.cash < 5000.0
    assert restored.realized_pnl == 0.0

    resumed = DryRunTrader(
        portfolio=restored,
        max_position_value=5000.0,
    )

    sell = resumed.process_signal(
        symbol="BTCUSDT",
        action=Action.SELL,
        price=110.0,
        confidence=0.90,
        risk_score=0.0,
        reason="deterministic lifecycle test exit",
    )

    assert sell.executed is True
    assert sell.action.value == "exit"
    assert sell.quantity > 0.0
    assert "BTCUSDT" not in restored.positions
    assert sell.realized_pnl > 0.0
    assert restored.realized_pnl == sell.realized_pnl
    assert restored.cash > 5000.0
    assert resumed.journal.trade_count == 1
    assert resumed.journal.latest().action == "exit"
    assert resumed.journal.latest().realized_pnl == sell.realized_pnl

    store.save(restored)
    final_state = store.load(initial_cash=5000.0)

    assert final_state.positions == {}
    assert final_state.realized_pnl == sell.realized_pnl
    assert final_state.cash == restored.cash
