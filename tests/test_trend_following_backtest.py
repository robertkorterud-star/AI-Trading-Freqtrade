import pytest

from atlas.trading.trend_following_backtest import (
    TrendFollowingBacktester,
)


def test_backtest_handles_insufficient_data():

    result = TrendFollowingBacktester(
        fast_period=3,
        slow_period=5,
    ).run(
        [100.0],
        initial_capital=10000.0,
    )

    assert result.final_capital == 10000.0
    assert result.strategy_return_percent == 0.0
    assert result.trade_count == 0


def test_backtest_bullish_market_can_open_position():

    closes = (
        list(range(100, 130))
        + list(range(130, 180))
    )

    result = TrendFollowingBacktester(
        fast_period=3,
        slow_period=8,
        transaction_cost_percent=0.0,
        slippage_percent=0.0,
    ).run(closes)

    assert result.trade_count >= 1
    assert result.final_capital > 10000.0
    assert result.strategy_return_percent > 0.0


def test_backtest_bearish_market_does_not_short():

    closes = list(
        range(200, 100, -1)
    )

    result = TrendFollowingBacktester(
        fast_period=3,
        slow_period=8,
        transaction_cost_percent=0.0,
        slippage_percent=0.0,
    ).run(closes)

    assert result.final_capital == 10000.0
    assert result.trade_count == 0


def test_buy_and_hold_is_calculated():

    closes = [
        100.0,
        110.0,
        120.0,
    ]

    result = TrendFollowingBacktester(
        fast_period=2,
        slow_period=3,
    ).run(closes)

    assert result.buy_and_hold_return_percent == pytest.approx(
        20.0
    )


def test_costs_reduce_trade_return():

    closes = (
        list(range(100, 130))
        + list(range(130, 180))
        + list(range(180, 120, -1))
    )

    free = TrendFollowingBacktester(
        fast_period=3,
        slow_period=8,
        transaction_cost_percent=0.0,
        slippage_percent=0.0,
    ).run(closes)

    costly = TrendFollowingBacktester(
        fast_period=3,
        slow_period=8,
        transaction_cost_percent=0.5,
        slippage_percent=0.5,
    ).run(closes)

    assert (
        costly.final_capital
        < free.final_capital
    )


def test_trade_statistics_are_consistent():

    closes = (
        list(range(100, 160))
        + list(range(160, 100, -1))
    )

    result = TrendFollowingBacktester(
        fast_period=3,
        slow_period=8,
        transaction_cost_percent=0.0,
        slippage_percent=0.0,
    ).run(closes)

    assert (
        result.winning_trades
        + result.losing_trades
        == result.trade_count
    )

    if result.trade_count:
        assert (
            result.win_rate_percent
            >= 0.0
        )

        assert (
            result.win_rate_percent
            <= 100.0
        )


def test_drawdown_is_zero_for_monotonic_equity():

    closes = list(
        range(100, 180)
    )

    result = TrendFollowingBacktester(
        fast_period=3,
        slow_period=8,
        transaction_cost_percent=0.0,
        slippage_percent=0.0,
    ).run(closes)

    assert (
        result.max_drawdown_percent
        <= 0.0
    )


def test_backtest_rejects_invalid_prices():

    try:
        TrendFollowingBacktester().run(
            [100.0, 0.0, 101.0]
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected ValueError."
        )


def test_backtest_does_not_create_live_decision():

    result = TrendFollowingBacktester(
        fast_period=3,
        slow_period=8,
    ).run(
        list(range(100, 160))
    )

    assert not hasattr(
        result,
        "decision",
    )

    assert not hasattr(
        result,
        "action",
    )

    assert not hasattr(
        result,
        "buy",
    )

    assert not hasattr(
        result,
        "sell",
    )


def test_backtest_accepts_historical_market_data():

    from datetime import datetime, timedelta

    from atlas.trading.historical_market_data import (
        HistoricalMarketData,
        OHLCVBar,
    )

    start = datetime(
        2026,
        1,
        1,
    )

    bars = [
        OHLCVBar(
            timestamp=start + timedelta(
                days=index
            ),
            open=float(100 + index),
            high=float(105 + index),
            low=float(99 + index),
            close=float(104 + index),
            volume=1000.0,
        )
        for index in range(40)
    ]

    data = HistoricalMarketData(
        symbol="BTC-USD",
        bars=bars,
    )

    result = TrendFollowingBacktester(
        fast_period=3,
        slow_period=8,
        transaction_cost_percent=0.0,
        slippage_percent=0.0,
    ).run(data)

    assert result.final_capital >= 10000.0
    assert result.buy_and_hold_return_percent > 0.0
