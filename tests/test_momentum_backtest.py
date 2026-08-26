from datetime import datetime, timedelta, timezone

import pytest

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
    OHLCVBar,
)
from atlas.trading.momentum_backtest import (
    MomentumBacktester,
)


def _data(closes):

    start = datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    bars = []
    previous = closes[0]

    for index, close in enumerate(closes):

        bars.append(
            OHLCVBar(
                timestamp=(
                    start
                    + timedelta(hours=index)
                ),
                open=previous,
                high=max(
                    previous,
                    close,
                ) + 1.0,
                low=min(
                    previous,
                    close,
                ) - 1.0,
                close=close,
                volume=1000.0,
            )
        )

        previous = close

    return HistoricalMarketData(
        symbol="BTC-USD",
        timeframe="4h",
        source="test",
        bars=bars,
    )


def test_momentum_backtest_runs():

    closes = [
        100.0 + index
        for index in range(40)
    ]

    result = MomentumBacktester(
        lookback_period=5,
    ).run(
        _data(closes)
    )

    assert result.strategy_return_percent > -100.0
    assert result.trade_count >= 0


def test_momentum_reports_buy_and_hold():

    closes = [
        100.0 + index
        for index in range(30)
    ]

    result = MomentumBacktester(
        lookback_period=5,
    ).run(
        _data(closes)
    )

    assert (
        result.buy_and_hold_return_percent
        == pytest.approx(29.0)
    )


def test_momentum_is_deterministic():

    data = _data(
        [
            100.0,
            101.0,
            102.0,
            103.0,
            104.0,
            105.0,
            104.0,
            103.0,
            102.0,
            101.0,
            100.0,
            101.0,
            102.0,
            103.0,
            104.0,
            105.0,
        ]
    )

    backtester = MomentumBacktester(
        lookback_period=3,
    )

    first = backtester.run(data)
    second = backtester.run(data)

    assert first == second


def test_lookback_must_be_positive():

    with pytest.raises(ValueError):

        MomentumBacktester(
            lookback_period=0,
        )


def test_short_dataset_returns_zero_result():

    data = _data(
        [
            100.0,
            101.0,
            102.0,
        ]
    )

    result = MomentumBacktester(
        lookback_period=5,
    ).run(data)

    assert result.strategy_return_percent == 0.0
    assert result.trade_count == 0


def test_momentum_handles_declining_market():

    closes = [
        100.0 - index
        for index in range(40)
    ]

    result = MomentumBacktester(
        lookback_period=5,
    ).run(
        _data(closes)
    )

    assert result.strategy_return_percent > -100.0
