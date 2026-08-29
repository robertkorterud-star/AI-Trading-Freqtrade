from atlas.models.action import Action
from atlas.trading.dry_run_trader import DryRunTrader
from atlas.trading.paper_portfolio import PaperPortfolio
from atlas.trading.trade_journal import TradeJournal


def test_paper_portfolio_buy_and_sell():
    portfolio = PaperPortfolio(
        initial_cash=10_000.0,
        fee_rate=0.0,
    )

    portfolio.buy(
        "BTC-USD",
        price=100.0,
        quantity=10.0,
    )

    assert portfolio.positions["BTC-USD"].quantity == 10.0

    pnl = portfolio.sell(
        "BTC-USD",
        price=120.0,
        quantity=10.0,
    )

    assert pnl == 200.0
    assert portfolio.realized_pnl == 200.0
    assert "BTC-USD" not in portfolio.positions


def test_paper_portfolio_marks_equity():
    portfolio = PaperPortfolio(
        initial_cash=10_000.0,
        fee_rate=0.0,
    )

    portfolio.buy(
        "BTC-USD",
        price=100.0,
        quantity=10.0,
    )

    # Cash after purchase: 9,000
    # Market value of 10 BTC at 110: 1,100
    # Total equity: 10,100
    assert portfolio.equity(
        {"BTC-USD": 110.0}
    ) == 10_100.0


def test_dry_run_enters_position():
    trader = DryRunTrader(
        portfolio=PaperPortfolio(
            initial_cash=100_000.0,
            fee_rate=0.0,
        ),
        journal=TradeJournal(),
        max_position_value=10_000.0,
    )

    result = trader.process_signal(
        "BTC-USD",
        Action.BUY,
        price=100.0,
        confidence=0.95,
        risk_score=0.10,
    )

    assert result.action.value == "enter"
    assert result.quantity > 0.0
    assert "BTC-USD" in trader.portfolio.positions
    assert trader.journal.trade_count == 1


def test_dry_run_strong_sell_exits():
    trader = DryRunTrader(
        portfolio=PaperPortfolio(
            initial_cash=100_000.0,
            fee_rate=0.0,
        ),
        journal=TradeJournal(),
        max_position_value=10_000.0,
    )

    trader.process_signal(
        "BTC-USD",
        Action.BUY,
        price=100.0,
        confidence=0.95,
        risk_score=0.10,
    )

    result = trader.process_signal(
        "BTC-USD",
        Action.SELL,
        price=105.0,
        confidence=0.95,
        risk_score=0.10,
    )

    assert result.action.value == "exit"
    assert "BTC-USD" not in trader.portfolio.positions
    assert trader.portfolio.realized_pnl > 0.0


def test_dry_run_weak_signal_does_not_trade():
    trader = DryRunTrader(
        portfolio=PaperPortfolio(
            initial_cash=100_000.0,
            fee_rate=0.0,
        ),
        journal=TradeJournal(),
        max_position_value=10_000.0,
    )

    result = trader.process_signal(
        "BTC-USD",
        Action.BUY,
        price=100.0,
        confidence=0.20,
        risk_score=0.10,
    )

    assert result.action.value == "hold"
    assert result.quantity == 0.0
    assert "BTC-USD" not in trader.portfolio.positions
