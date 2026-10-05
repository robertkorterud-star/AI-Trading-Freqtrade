import pytest

from atlas.trading.backtest_analyzer import BacktestAnalyzer
from atlas.trading.trade_journal import TradeJournal
from atlas.trading.trading_cost_model import TradingCostModel


def _record(
    journal,
    *,
    action,
    quantity,
    price,
    fee=0.0,
    realized_pnl=0.0,
    symbol="BTC-USD",
):
    journal.record(
        symbol=symbol,
        action=action,
        quantity=quantity,
        price=price,
        fee=fee,
        realized_pnl=realized_pnl,
        reason="test",
        confidence=0.9,
        risk_score=0.1,
        equity_after=100_000.0,
    )


def test_analyzer_ignores_non_executed_hold_records():
    journal = TradeJournal()

    _record(
        journal,
        action="hold",
        quantity=0.0,
        price=100.0,
    )

    report = BacktestAnalyzer().analyze(journal)

    assert report.execution_count == 0
    assert report.completed_exit_count == 0
    assert report.turnover == 0.0
    assert report.gross_pnl == 0.0
    assert report.actual_fees == 0.0
    assert report.estimated_spread_slippage == 0.0
    assert report.net_pnl == 0.0
    assert report.net_expectancy == 0.0


def test_analyzer_accounts_for_complete_round_trip_costs():
    journal = TradeJournal()

    _record(
        journal,
        action="enter",
        quantity=10.0,
        price=100.0,
        fee=1.0,
    )
    _record(
        journal,
        action="exit",
        quantity=10.0,
        price=110.0,
        fee=1.1,
        realized_pnl=98.9,
    )

    cost_model = TradingCostModel(
        fee_rate=0.001,
        spread_bps=2.0,
        slippage_bps=1.0,
    )

    report = BacktestAnalyzer(
        cost_model=cost_model,
    ).analyze(journal)

    # Two executed sides.
    assert report.execution_count == 2

    # One realized exit event.
    assert report.completed_exit_count == 1

    # Buy notional 1,000 + sell notional 1,100.
    assert report.turnover == pytest.approx(2_100.0)

    # Gross market P&L before all direct trading costs.
    assert report.gross_pnl == pytest.approx(100.0)

    # Actual portfolio fees from both sides.
    assert report.actual_fees == pytest.approx(2.1)

    # TradingCostModel applies half of the quoted 2 bps spread
    # plus 1 bp slippage on each executed side: 2 bps per side.
    assert report.estimated_spread_slippage == pytest.approx(
        1_000.0 * 0.0002 + 1_100.0 * 0.0002
    )

    assert report.net_pnl == pytest.approx(
        100.0 - 2.1 - 0.42
    )
    assert report.net_expectancy == pytest.approx(
        report.net_pnl
    )


def test_analyzer_handles_accumulation_and_partial_reduce():
    journal = TradeJournal()

    _record(
        journal,
        action="enter",
        quantity=10.0,
        price=100.0,
        fee=0.0,
    )
    _record(
        journal,
        action="enter",
        quantity=10.0,
        price=80.0,
        fee=0.0,
    )

    # Average cost is now 90. Sell half at 100:
    # gross realized P&L = (100 - 90) * 10 = 100.
    _record(
        journal,
        action="reduce",
        quantity=10.0,
        price=100.0,
        fee=0.0,
        realized_pnl=100.0,
    )

    # Remaining 10 exit at 110:
    # gross realized P&L = (110 - 90) * 10 = 200.
    _record(
        journal,
        action="exit",
        quantity=10.0,
        price=110.0,
        fee=0.0,
        realized_pnl=200.0,
    )

    report = BacktestAnalyzer(
        cost_model=TradingCostModel(
            fee_rate=0.0,
            spread_bps=0.0,
            slippage_bps=0.0,
        )
    ).analyze(journal)

    assert report.execution_count == 4
    assert report.completed_exit_count == 2
    assert report.realized_exit_count == 2
    assert report.completed_trade_count == 1
    assert report.gross_pnl == pytest.approx(300.0)
    assert report.net_pnl == pytest.approx(300.0)
    assert report.net_expectancy == pytest.approx(300.0)

    assert report.turnover == pytest.approx(
        1_000.0 + 800.0 + 1_000.0 + 1_100.0
    )


def test_analyzer_net_pnl_matches_closed_paper_portfolio_economics():
    from atlas.models.action import Action
    from atlas.trading.dry_run_trader import DryRunTrader
    from atlas.trading.paper_portfolio import PaperPortfolio

    initial_cash = 10_000.0
    portfolio = PaperPortfolio(
        initial_cash=initial_cash,
        fee_rate=0.001,
    )
    journal = TradeJournal()

    trader = DryRunTrader(
        portfolio=portfolio,
        journal=journal,
        max_position_value=1_000.0,
    )

    entry = trader.process_signal(
        "BTC-USD",
        Action.BUY,
        price=100.0,
        confidence=0.95,
        risk_score=0.10,
    )

    assert entry.executed is True
    assert entry.quantity > 0.0

    exit_result = trader.process_signal(
        "BTC-USD",
        Action.SELL,
        price=110.0,
        confidence=0.95,
        risk_score=0.10,
    )

    assert exit_result.executed is True
    assert "BTC-USD" not in portfolio.positions

    report = BacktestAnalyzer(
        cost_model=TradingCostModel(
            fee_rate=portfolio.fee_rate,
            spread_bps=0.0,
            slippage_bps=0.0,
        )
    ).analyze(journal)

    # With no modeled spread/slippage, Analyzer net P&L must equal
    # the actual closed-account change produced by PaperPortfolio.
    actual_closed_pnl = portfolio.cash - initial_cash

    assert report.actual_fees > 0.0
    assert report.estimated_spread_slippage == 0.0
    assert report.net_pnl == pytest.approx(actual_closed_pnl)


def test_analyzer_matches_portfolio_with_accumulation_and_partial_reduction():
    from atlas.models.action import Action
    from atlas.trading.dry_run_trader import DryRunTrader
    from atlas.trading.paper_portfolio import PaperPortfolio

    initial_cash = 10_000.0
    portfolio = PaperPortfolio(
        initial_cash=initial_cash,
        fee_rate=0.001,
    )
    journal = TradeJournal()

    trader = DryRunTrader(
        portfolio=portfolio,
        journal=journal,
        max_position_value=1_000.0,
    )

    first = trader.process_signal(
        "BTC-USD",
        Action.BUY,
        price=100.0,
        confidence=0.95,
        risk_score=0.10,
    )
    assert first.executed is True
    assert first.quantity > 0.0

    # Price drop exceeds the existing 2% accumulation threshold.
    second = trader.process_signal(
        "BTC-USD",
        Action.BUY,
        price=95.0,
        confidence=0.95,
        risk_score=0.10,
    )
    assert second.executed is True
    assert second.quantity > 0.0

    # Moderate SELL produces REDUCE rather than full EXIT.
    reduced = trader.process_signal(
        "BTC-USD",
        Action.SELL,
        price=105.0,
        confidence=0.50,
        risk_score=0.10,
    )
    assert reduced.executed is True
    assert reduced.action.value == "reduce"
    assert reduced.quantity > 0.0
    assert "BTC-USD" in portfolio.positions

    # Strong SELL closes the remaining position.
    exited = trader.process_signal(
        "BTC-USD",
        Action.SELL,
        price=110.0,
        confidence=0.95,
        risk_score=0.10,
    )
    assert exited.executed is True
    assert exited.action.value == "exit"
    assert "BTC-USD" not in portfolio.positions

    report = BacktestAnalyzer(
        cost_model=TradingCostModel(
            fee_rate=portfolio.fee_rate,
            spread_bps=0.0,
            slippage_bps=0.0,
        )
    ).analyze(journal)

    actual_closed_pnl = portfolio.cash - initial_cash

    assert report.execution_count == 4
    assert report.completed_exit_count == 2
    assert report.actual_fees > 0.0
    assert report.estimated_spread_slippage == 0.0
    assert report.net_pnl == pytest.approx(actual_closed_pnl)


def test_analyzer_counts_completed_position_lifecycle_not_exit_events():
    journal = TradeJournal()

    # One position lifecycle with accumulation.
    _record(
        journal,
        action="enter",
        quantity=10.0,
        price=100.0,
    )
    _record(
        journal,
        action="enter",
        quantity=10.0,
        price=90.0,
    )

    # Partial realization does not complete the trade lifecycle.
    _record(
        journal,
        action="reduce",
        quantity=5.0,
        price=105.0,
        realized_pnl=50.0,
    )

    # Even an EXIT-labelled execution may be quantity-limited by canonical
    # risk approval, so action alone cannot prove that the position is closed.
    _record(
        journal,
        action="exit",
        quantity=5.0,
        price=108.0,
        realized_pnl=65.0,
    )

    # Remaining quantity is finally closed here.
    _record(
        journal,
        action="exit",
        quantity=10.0,
        price=110.0,
        realized_pnl=150.0,
    )

    report = BacktestAnalyzer(
        cost_model=TradingCostModel(
            fee_rate=0.0,
            spread_bps=0.0,
            slippage_bps=0.0,
        )
    ).analyze(journal)

    assert report.realized_exit_count == 3
    assert report.completed_trade_count == 1


def test_analyzer_net_expectancy_is_per_completed_trade_lifecycle():
    journal = TradeJournal()

    _record(
        journal,
        action="enter",
        quantity=20.0,
        price=100.0,
    )
    _record(
        journal,
        action="reduce",
        quantity=5.0,
        price=105.0,
        realized_pnl=25.0,
    )
    _record(
        journal,
        action="exit",
        quantity=15.0,
        price=110.0,
        realized_pnl=150.0,
    )

    report = BacktestAnalyzer(
        cost_model=TradingCostModel(
            fee_rate=0.0,
            spread_bps=0.0,
            slippage_bps=0.0,
        )
    ).analyze(journal)

    assert report.realized_exit_count == 2
    assert report.completed_trade_count == 1
    assert report.net_pnl == pytest.approx(175.0)
    assert report.net_expectancy == pytest.approx(175.0)


def test_analyzer_does_not_count_open_position_as_completed_trade():
    journal = TradeJournal()

    _record(
        journal,
        action="enter",
        symbol="BTC/USDT",
        quantity=10.0,
        price=100.0,
        fee=1.0,
    )
    _record(
        journal,
        action="reduce",
        symbol="BTC/USDT",
        quantity=4.0,
        price=110.0,
        fee=0.44,
        realized_pnl=39.56,
    )

    report = BacktestAnalyzer(
        cost_model=TradingCostModel(
            fee_rate=0.0,
            spread_bps=0.0,
            slippage_bps=0.0,
        )
    ).analyze(journal)

    assert report.execution_count == 2
    assert report.realized_exit_count == 1
    assert report.completed_trade_count == 0
    assert report.net_expectancy == 0.0


def test_analyzer_expectancy_excludes_costs_from_open_lifecycle():
    journal = TradeJournal()

    # Completed lifecycle: +100 gross, no direct costs.
    _record(
        journal,
        action="enter",
        symbol="BTC/USDT",
        quantity=10.0,
        price=100.0,
        fee=0.0,
    )
    _record(
        journal,
        action="exit",
        symbol="BTC/USDT",
        quantity=10.0,
        price=110.0,
        fee=0.0,
        realized_pnl=100.0,
    )

    # A new lifecycle starts but remains open at the end of the journal.
    # Its entry fee belongs to aggregate execution economics, not to the
    # expectancy of the already completed trade.
    _record(
        journal,
        action="enter",
        symbol="ETH/USDT",
        quantity=10.0,
        price=100.0,
        fee=10.0,
    )

    report = BacktestAnalyzer(
        cost_model=TradingCostModel(
            fee_rate=0.0,
            spread_bps=0.0,
            slippage_bps=0.0,
        )
    ).analyze(journal)

    assert report.completed_trade_count == 1
    assert report.net_pnl == pytest.approx(90.0)
    assert report.net_expectancy == pytest.approx(100.0)
