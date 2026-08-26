import pytest

from atlas.trading.walk_forward import (
    TrendFollowingWalkForward,
)


def test_walk_forward_creates_chronological_windows():

    closes = list(
        range(100, 200)
    )

    result = TrendFollowingWalkForward(
        fast_period=3,
        slow_period=8,
        transaction_cost_percent=0.0,
        slippage_percent=0.0,
    ).evaluate(
        closes,
        train_size=40,
        test_size=20,
    )

    assert result.total_points == 100
    assert result.train_size == 40
    assert result.test_size == 20
    assert result.step_size == 20

    assert len(result.windows) == 3

    assert result.windows[0].train_start == 0
    assert result.windows[0].train_end == 40
    assert result.windows[0].test_start == 40
    assert result.windows[0].test_end == 60

    assert result.windows[1].train_start == 20
    assert result.windows[1].train_end == 60
    assert result.windows[1].test_start == 60
    assert result.windows[1].test_end == 80


def test_walk_forward_never_uses_future_test_data():

    closes = list(
        range(100, 200)
    )

    result = TrendFollowingWalkForward(
        fast_period=3,
        slow_period=8,
    ).evaluate(
        closes,
        train_size=40,
        test_size=20,
    )

    for window in result.windows:
        assert (
            window.train_end
            == window.test_start
        )

        assert (
            window.train_end
            <= window.test_start
        )

        assert (
            window.test_start
            < window.test_end
        )


def test_walk_forward_handles_too_little_data():

    result = TrendFollowingWalkForward().evaluate(
        list(range(1, 101)),
        train_size=80,
        test_size=30,
    )

    assert result.windows == ()
    assert result.total_strategy_return_percent == 0.0
    assert (
        result.total_buy_and_hold_return_percent
        == 0.0
    )


def test_walk_forward_rejects_invalid_sizes():

    evaluator = TrendFollowingWalkForward()

    with pytest.raises(ValueError):
        evaluator.evaluate(
            list(range(100)),
            train_size=0,
            test_size=10,
        )

    with pytest.raises(ValueError):
        evaluator.evaluate(
            list(range(100)),
            train_size=10,
            test_size=0,
        )

    with pytest.raises(ValueError):
        evaluator.evaluate(
            list(range(100)),
            train_size=10,
            test_size=10,
            step_size=0,
        )


def test_walk_forward_compounds_returns():

    closes = list(
        range(100, 250)
    )

    result = TrendFollowingWalkForward(
        fast_period=3,
        slow_period=8,
        transaction_cost_percent=0.0,
        slippage_percent=0.0,
    ).evaluate(
        closes,
        train_size=50,
        test_size=25,
    )

    expected = 1.0

    for window in result.windows:
        expected *= (
            1.0
            + window.test_return_percent
            / 100.0
        )

    expected = (
        expected - 1.0
    ) * 100.0

    assert (
        result.total_strategy_return_percent
        == pytest.approx(expected)
    )


def test_walk_forward_counts_positive_and_negative_windows():

    closes = (
        list(range(100, 180))
        + list(range(180, 100, -1))
        + list(range(100, 190))
    )

    result = TrendFollowingWalkForward(
        fast_period=3,
        slow_period=8,
        transaction_cost_percent=0.0,
        slippage_percent=0.0,
    ).evaluate(
        closes,
        train_size=60,
        test_size=30,
    )

    assert (
        result.positive_windows
        + result.negative_windows
        <= len(result.windows)
    )


def test_walk_forward_is_deterministic():

    closes = (
        list(range(100, 180))
        + list(range(180, 120, -1))
    )

    evaluator = TrendFollowingWalkForward(
        fast_period=5,
        slow_period=15,
        transaction_cost_percent=0.1,
        slippage_percent=0.05,
    )

    first = evaluator.evaluate(
        closes,
        train_size=50,
        test_size=20,
    )

    second = evaluator.evaluate(
        closes,
        train_size=50,
        test_size=20,
    )

    assert first == second


def test_walk_forward_rejects_invalid_prices():

    evaluator = TrendFollowingWalkForward()

    with pytest.raises(ValueError):
        evaluator.evaluate(
            [100.0, 101.0, 0.0, 102.0],
            train_size=2,
            test_size=2,
        )


def test_walk_forward_accepts_historical_market_data():

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
        for index in range(100)
    ]

    data = HistoricalMarketData(
        symbol="BTC-USD",
        bars=bars,
    )

    result = TrendFollowingWalkForward(
        fast_period=3,
        slow_period=8,
        transaction_cost_percent=0.0,
        slippage_percent=0.0,
    ).evaluate(
        data,
        train_size=40,
        test_size=20,
    )

    assert result.total_points == 100
    assert len(result.windows) == 3

    for window in result.windows:
        assert window.train_end == window.test_start
        assert window.test_start < window.test_end
