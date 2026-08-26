from atlas.trading.trend_following_backtest import (
    TrendFollowingBacktester,
)


def test_bull_market_strategy_does_not_beat_price_data_with_magic():

    closes = list(range(100, 200))

    result = TrendFollowingBacktester(
        fast_period=5,
        slow_period=15,
        transaction_cost_percent=0.0,
        slippage_percent=0.0,
    ).run(closes)

    assert result.strategy_return_percent <= (
        result.buy_and_hold_return_percent
    )


def test_bear_market_preserves_capital_when_long_only():

    closes = list(range(200, 100, -1))

    result = TrendFollowingBacktester(
        fast_period=5,
        slow_period=15,
        transaction_cost_percent=0.0,
        slippage_percent=0.0,
    ).run(closes)

    assert result.final_capital == 10000.0
    assert result.strategy_return_percent == 0.0


def test_flat_market_cannot_create_profit():

    closes = [100.0] * 100

    result = TrendFollowingBacktester(
        fast_period=3,
        slow_period=8,
        transaction_cost_percent=0.0,
        slippage_percent=0.0,
    ).run(closes)

    assert result.final_capital == 10000.0
    assert result.strategy_return_percent == 0.0
    assert result.trade_count == 0
    assert result.trade_count >= 0


def test_reversal_market_can_close_position():

    closes = (
        list(range(100, 160))
        + list(range(160, 90, -1))
    )

    result = TrendFollowingBacktester(
        fast_period=5,
        slow_period=15,
        transaction_cost_percent=0.0,
        slippage_percent=0.0,
    ).run(closes)

    assert result.trade_count >= 1

    assert all(
        trade.entry_index < trade.exit_index
        for trade in result.trades
    )


def test_costs_never_improve_strategy_result():

    closes = (
        list(range(100, 170))
        + list(range(170, 110, -1))
        + list(range(110, 180))
    )

    free = TrendFollowingBacktester(
        fast_period=5,
        slow_period=15,
        transaction_cost_percent=0.0,
        slippage_percent=0.0,
    ).run(closes)

    costly = TrendFollowingBacktester(
        fast_period=5,
        slow_period=15,
        transaction_cost_percent=0.5,
        slippage_percent=0.5,
    ).run(closes)

    assert (
        costly.final_capital
        <= free.final_capital
    )


def test_trade_indices_are_chronological():

    closes = (
        list(range(100, 170))
        + list(range(170, 110, -1))
        + list(range(110, 180))
    )

    result = TrendFollowingBacktester(
        fast_period=5,
        slow_period=15,
        transaction_cost_percent=0.0,
        slippage_percent=0.0,
    ).run(closes)

    previous_exit = -1

    for trade in result.trades:
        assert trade.entry_index > previous_exit
        assert trade.entry_index < trade.exit_index
        previous_exit = trade.exit_index


def test_drawdown_never_positive():

    closes = (
        list(range(100, 160))
        + list(range(160, 90, -1))
    )

    result = TrendFollowingBacktester(
        fast_period=5,
        slow_period=15,
    ).run(closes)

    assert result.max_drawdown_percent <= 0.0


def test_transaction_cost_and_slippage_are_reported():

    result = TrendFollowingBacktester(
        transaction_cost_percent=0.2,
        slippage_percent=0.1,
    ).run(
        list(range(100, 160))
    )

    assert result.transaction_cost_percent == 0.2
    assert result.slippage_percent == 0.1


def test_backtest_is_deterministic():

    closes = (
        list(range(100, 160))
        + list(range(160, 100, -1))
    )

    backtester = TrendFollowingBacktester(
        fast_period=5,
        slow_period=15,
        transaction_cost_percent=0.1,
        slippage_percent=0.05,
    )

    first = backtester.run(closes)
    second = backtester.run(closes)

    assert first == second
