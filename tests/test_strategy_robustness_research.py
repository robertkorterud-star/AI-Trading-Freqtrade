from datetime import datetime, timedelta, timezone

import pytest

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
    OHLCVBar,
)
from atlas.trading.strategy_robustness_research import (
    StrategyRobustnessResearch,
)


def _data(
    symbol="BTC-USD",
    timeframe="4h",
    source="test",
    direction=1.0,
):
    start = datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    bars = []
    price = 100.0

    for index in range(120):

        close = price + direction

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
        symbol=symbol,
        timeframe=timeframe,
        source=source,
        bars=bars,
    )


def test_robustness_research_runs_across_datasets():

    datasets = [
        _data(
            symbol="BTC-USD",
            timeframe="4h",
        ),
        _data(
            symbol="ETH-USD",
            timeframe="4h",
        ),
    ]

    result = StrategyRobustnessResearch().run(
        datasets,
        fast_period=5,
        slow_period=15,
        train_size=50,
        test_size=20,
    )

    assert len(result.results) == 2
    assert result.datasets_tested == 2

    assert result.results[0].symbol == "BTC-USD"
    assert result.results[1].symbol == "ETH-USD"


def test_robustness_preserves_dataset_metadata():

    result = StrategyRobustnessResearch().run(
        [
            _data(
                symbol="BTC-USD",
                timeframe="4h",
                source="coingecko",
            ),
        ],
        fast_period=5,
        slow_period=15,
        train_size=50,
        test_size=20,
    )

    item = result.results[0]

    assert item.symbol == "BTC-USD"
    assert item.timeframe == "4h"
    assert item.source == "coingecko"


def test_robustness_calculates_advantage():

    result = StrategyRobustnessResearch().run(
        [
            _data(),
        ],
        fast_period=5,
        slow_period=15,
        train_size=50,
        test_size=20,
    )

    item = result.results[0]

    assert (
        item.advantage_percent
        == pytest.approx(
            item.walk_forward_return_percent
            - item.buy_and_hold_return_percent
        )
    )


def test_robustness_summary_counts_outperformance():

    result = StrategyRobustnessResearch().run(
        [
            _data(
                symbol="BTC-USD",
            ),
            _data(
                symbol="ETH-USD",
            ),
        ],
        fast_period=5,
        slow_period=15,
        train_size=50,
        test_size=20,
    )

    assert (
        result.datasets_outperformed
        == sum(
            item.outperformed_buy_and_hold
            for item in result.results
        )
    )

    assert (
        result.outperformance_ratio_percent
        == pytest.approx(
            result.datasets_outperformed
            / result.datasets_tested
            * 100.0
        )
    )


def test_robustness_requires_majority_outperformance():

    result = StrategyRobustnessResearch().run(
        [
            _data(
                symbol="BTC-USD",
            ),
            _data(
                symbol="ETH-USD",
            ),
            _data(
                symbol="SOL-USD",
            ),
        ],
        fast_period=5,
        slow_period=15,
        train_size=50,
        test_size=20,
    )

    expected = (
        result.datasets_outperformed
        > result.datasets_tested / 2
    )

    assert result.robust is expected


def test_best_result_is_available():

    result = StrategyRobustnessResearch().run(
        [
            _data(),
        ],
        fast_period=5,
        slow_period=15,
        train_size=50,
        test_size=20,
    )

    assert result.best is not None
    assert result.best in result.results


def test_empty_dataset_collection_is_not_robust():

    result = StrategyRobustnessResearch().run(
        [],
        fast_period=5,
        slow_period=15,
        train_size=50,
        test_size=20,
    )

    assert result.datasets_tested == 0
    assert result.datasets_outperformed == 0
    assert (
        result.outperformance_ratio_percent
        == 0.0
    )
    assert (
        result.average_advantage_percent
        == 0.0
    )
    assert result.robust is False
    assert result.best is None


def test_fast_period_must_be_smaller():

    with pytest.raises(ValueError):

        StrategyRobustnessResearch().run(
            [_data()],
            fast_period=15,
            slow_period=5,
            train_size=50,
            test_size=20,
        )


def test_periods_must_be_positive():

    with pytest.raises(ValueError):

        StrategyRobustnessResearch().run(
            [_data()],
            fast_period=0,
            slow_period=15,
            train_size=50,
            test_size=20,
        )


def test_robustness_is_deterministic():

    datasets = [
        _data(
            symbol="BTC-USD",
        ),
        _data(
            symbol="ETH-USD",
        ),
    ]

    research = StrategyRobustnessResearch()

    first = research.run(
        datasets,
        fast_period=5,
        slow_period=15,
        train_size=50,
        test_size=20,
    )

    second = research.run(
        datasets,
        fast_period=5,
        slow_period=15,
        train_size=50,
        test_size=20,
    )

    assert first == second
