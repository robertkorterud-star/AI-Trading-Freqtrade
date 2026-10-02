from datetime import datetime, timedelta, timezone

import pytest

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
    OHLCVBar,
)
from atlas.trading.mean_reversion_walk_forward import (
    MeanReversionWalkForward,
)


def _data():

    start = datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    bars = []

    price = 100.0

    for index in range(120):

        if index % 20 == 10:
            close = price * 0.95
        else:
            close = price * 1.005

        bars.append(
            OHLCVBar(
                timestamp=(
                    start
                    + timedelta(hours=index)
                ),
                open=price,
                high=max(
                    price,
                    close,
                ) + 1.0,
                low=min(
                    price,
                    close,
                ) - 1.0,
                close=close,
                volume=1000.0,
            )
        )

        price = close

    return HistoricalMarketData(
        symbol="BTC-USD",
        timeframe="4h",
        source="test",
        bars=bars,
    )


def test_mean_reversion_walk_forward_runs():

    result = MeanReversionWalkForward(
        lookback_period=5,
        entry_deviation_percent=2.0,
    ).evaluate(
        _data(),
        train_size=50,
        test_size=20,
    )

    assert len(result.windows) > 0
    assert len(result.windows) == 3


def test_walk_forward_preserves_benchmark():

    result = MeanReversionWalkForward(
        lookback_period=5,
        entry_deviation_percent=2.0,
    ).evaluate(
        _data(),
        train_size=50,
        test_size=20,
    )

    assert isinstance(
        result.total_buy_and_hold_return_percent,
        float,
    )


def test_positive_and_negative_windows_are_counted():

    result = MeanReversionWalkForward(
        lookback_period=5,
        entry_deviation_percent=2.0,
    ).evaluate(
        _data(),
        train_size=50,
        test_size=20,
    )

    assert (
        result.positive_windows
        + result.negative_windows
        == len(result.windows)
    )


def test_walk_forward_is_deterministic():

    data = _data()

    evaluator = MeanReversionWalkForward(
        lookback_period=5,
        entry_deviation_percent=2.0,
    )

    first = evaluator.evaluate(
        data,
        train_size=50,
        test_size=20,
    )

    second = evaluator.evaluate(
        data,
        train_size=50,
        test_size=20,
    )

    assert first == second


def test_train_size_must_be_positive():

    with pytest.raises(ValueError):

        MeanReversionWalkForward().evaluate(
            _data(),
            train_size=0,
            test_size=20,
        )


def test_test_size_must_be_positive():

    with pytest.raises(ValueError):

        MeanReversionWalkForward().evaluate(
            _data(),
            train_size=50,
            test_size=0,
        )


def test_large_windows_can_produce_no_results():

    result = MeanReversionWalkForward().evaluate(
        _data(),
        train_size=200,
        test_size=50,
    )

    assert result.windows == ()
    assert result.positive_windows == 0
    assert result.negative_windows == 0


def test_walk_forward_uses_pre_test_history_for_lookback():

    result = MeanReversionWalkForward(
        lookback_period=20,
        entry_deviation_percent=0.1,
    ).evaluate(
        _data(),
        train_size=50,
        test_size=20,
    )

    assert any(
        window.strategy_return_percent != 0.0
        for window in result.windows
    )
