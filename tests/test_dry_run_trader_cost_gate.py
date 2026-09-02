from atlas.models.action import Action
from atlas.trading.dry_run_trader import DryRunTrader
from atlas.trading.paper_portfolio import PaperPortfolio
from atlas.trading.trade_journal import TradeJournal
from atlas.trading.trading_cost_model import TradingCostModel


def make_trader() -> DryRunTrader:
    return DryRunTrader(
        portfolio=PaperPortfolio(
            initial_cash=100_000.0,
            fee_rate=0.001,
        ),
        journal=TradeJournal(),
        cost_model=TradingCostModel(
            fee_rate=0.001,
            spread_bps=4.0,
            slippage_bps=2.0,
        ),
        max_position_value=10_000.0,
    )


def test_buy_is_blocked_when_expected_return_is_below_trading_costs():
    trader = make_trader()

    result = trader.process_signal(
        "BTC-USD",
        Action.BUY,
        price=100.0,
        confidence=0.95,
        risk_score=0.10,
        expected_return=0.002,
    )

    assert result.executed is False
    assert result.action.value == "hold"
    assert result.quantity == 0.0
    assert "Trading cost blocked" in result.reason
    assert "0.28%" in result.reason
    assert trader.journal.trade_count == 0
    assert "BTC-USD" not in trader.portfolio.positions


def test_buy_is_allowed_when_expected_return_exceeds_trading_costs():
    trader = make_trader()

    result = trader.process_signal(
        "BTC-USD",
        Action.BUY,
        price=100.0,
        confidence=0.95,
        risk_score=0.10,
        expected_return=0.008,
    )

    assert result.executed is True
    assert result.action.value == "enter"
    assert result.quantity > 0.0
    assert trader.journal.trade_count == 1
    assert "BTC-USD" in trader.portfolio.positions


def test_cost_gate_does_not_block_exit():
    trader = make_trader()

    trader.process_signal(
        "BTC-USD",
        Action.BUY,
        price=100.0,
        confidence=0.95,
        risk_score=0.10,
        expected_return=0.008,
    )

    result = trader.process_signal(
        "BTC-USD",
        Action.SELL,
        price=100.0,
        confidence=0.95,
        risk_score=0.10,
        expected_return=0.0,
    )

    assert result.executed is True
    assert result.action.value == "exit"
    assert "BTC-USD" not in trader.portfolio.positions


def test_cost_model_defaults_to_paper_portfolio_fee_rate():
    trader = DryRunTrader(
        portfolio=PaperPortfolio(
            initial_cash=100_000.0,
            fee_rate=0.002,
        ),
        journal=TradeJournal(),
    )

    assert trader.cost_model.fee_rate == 0.002
