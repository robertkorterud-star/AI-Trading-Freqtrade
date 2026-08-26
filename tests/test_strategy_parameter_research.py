from datetime import datetime, timedelta, timezone

import pytest

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
    OHLCVBar,
)
from atlas.trading.strategy_parameter_research import (
    StrategyParameterResearch,
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

        close = price + (
            1.0
            if index < 60
            else -0.25
        )

        bars.append(
            OHLCVBar(
                timestamp=(
                    start
                    + timedelta(hours=index)
                ),
                open=price,
                high=max(price, close) + 1.0,
                low=min(price, close) - 1.0,
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


def test_parameter_research_runs_multiple_parameter_sets():

    result = StrategyParameterResearch().run(
        _data(),
        parameter_sets=[
            (3, 10),
            (5, 15),
            (8, 21),
        ],
        train_size=50,
        test_size=20,
    )

    assert len(result.results) == 3

    assert (
        result.results[0].fast_period
        == 3
    )

    assert (
        result.results[0].slow_period
        == 10
    )


def test_parameter_research_exposes_best_result():

    result = StrategyParameterResearch().run(
        _data(),
        parameter_sets=[
            (3, 10),
            (5, 15),
            (8, 21),
        ],
        train_size=50,
        test_size=20,
    )

    assert result.best is not None
    assert result.best in result.results


def test_parameter_research_is_deterministic():

    data = _data()

    research = StrategyParameterResearch()

    parameter_sets = [
        (3, 10),
        (5, 15),
        (8, 21),
    ]

    first = research.run(
        data,
        parameter_sets=parameter_sets,
        train_size=50,
        test_size=20,
    )

    second = research.run(
        data,
        parameter_sets=parameter_sets,
        train_size=50,
        test_size=20,
    )

    assert first == second


def test_fast_period_must_be_smaller_than_slow_period():

    with pytest.raises(ValueError):

        StrategyParameterResearch().run(
            _data(),
            parameter_sets=[
                (15, 5),
            ],
            train_size=50,
            test_size=20,
        )


def test_periods_must_be_positive():

    with pytest.raises(ValueError):

        StrategyParameterResearch().run(
            _data(),
            parameter_sets=[
                (0, 10),
            ],
            train_size=50,
            test_size=20,
        )


def test_empty_parameter_set_is_supported():

    result = StrategyParameterResearch().run(
        _data(),
        parameter_sets=[],
        train_size=50,
        test_size=20,
    )

    assert result.results == ()
    assert result.best is None
