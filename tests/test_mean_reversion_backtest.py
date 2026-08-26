from datetime import datetime, timedelta, timezone

import pytest

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
    OHLCVBar,
)
from atlas.trading.mean_reversion_backtest import (
    MeanReversionBacktester,
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


def test_mean_reversion_backtest_runs():

    closes = [
        100.0,
        100.0,
        100.0,
        100.0,
        95.0,
        96.0,
        97.0,
        98.0,
        99.0,
        100.0,
        101.0,
        102.0,
        103.0,
        104.0,
        105.0,
        106.0,
        107.0,
        108.0,
        109.0,
        110.0,
        111.0,
        112.0,
        113.0,
        114.0,
        115.0,
    ]

    result = MeanReversionBacktester(
        lookback_period=5,
        entry_deviation_percent=2.0,
    ).run(
        _data(closes)
    )

    assert result.trade_count >= 0
    assert result.strategy_return_percent > -100.0


def test_mean_reversion_reports_buy_and_hold():

    closes = [
        100.0 + index
        for index in range(30)
    ]

    result = MeanReversionBacktester(
        lookback_period=5,
        entry_deviation_percent=2.0,
    ).run(
        _data(closes)
    )

    assert (
        result.buy_and_hold_return_percent
        == pytest.approx(29.0)
    )


def test_mean_reversion_is_deterministic():

    data = _data(
        [
            100.0,
            100.0,
            100.0,
            100.0,
            95.0,
            96.0,
            97.0,
            98.0,
            99.0,
            100.0,
            101.0,
            100.0,
            99.0,
            98.0,
            97.0,
            96.0,
            95.0,
            100.0,
            101.0,
            102.0,
        ]
    )

    backtester = MeanReversionBacktester(
        lookback_period=5,
        entry_deviation_percent=2.0,
    )

    first = backtester.run(data)
    second = backtester.run(data)

    assert first == second


def test_lookback_must_be_valid():

    with pytest.raises(ValueError):

        MeanReversionBacktester(
            lookback_period=1,
        )


def test_entry_deviation_must_be_positive():

    with pytest.raises(ValueError):

        MeanReversionBacktester(
            entry_deviation_percent=0.0,
        )


def test_short_dataset_returns_zero_result():

    data = _data(
        [
            100.0,
            101.0,
            102.0,
        ]
    )

    result = MeanReversionBacktester(
        lookback_period=5,
    ).run(data)

    assert result.strategy_return_percent == 0.0
    assert result.trade_count == 0
