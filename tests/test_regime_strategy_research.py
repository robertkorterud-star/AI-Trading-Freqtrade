import pytest

from datetime import datetime, timedelta

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
    OHLCVBar,
)
from atlas.trading.regime_strategy_research import (
    RegimeStrategyResearch,
)


def _data(
    closes=None,
):
    if closes is None:
        closes = [
            100.0 + index
            for index in range(120)
        ]

    bars = []

    for index, close in enumerate(closes):
        bars.append(
            OHLCVBar(
                timestamp=datetime(
                    2026,
                    1,
                    1,
                ) + timedelta(hours=index),
                open=close,
                high=close,
                low=close,
                close=close,
                volume=1000.0,
            )
        )

    return HistoricalMarketData(
        symbol="BTC-USD",
        bars=bars,
        timeframe="4h",
        source="test",
    )


def test_forward_period_must_be_positive():

    with pytest.raises(ValueError):

        RegimeStrategyResearch(
            forward_period=0,
        )


def test_short_dataset_returns_empty_summary():

    result = RegimeStrategyResearch(
        forward_period=5,
    ).run(
        _data([100.0, 101.0, 102.0])
    )

    assert result.results == ()
    assert result.overall_best_strategy is None
    assert result.best_strategy_by_regime == {}


def test_all_strategy_families_are_present():

    result = RegimeStrategyResearch().run(
        _data()
    )

    names = {
        item.strategy_name
        for item in result.results
    }

    assert names == {
        "Trend Following",
        "Mean Reversion",
        "Momentum",
    }


def test_forward_return_uses_future_candle():

    result = RegimeStrategyResearch(
        forward_period=1,
    ).run(
        _data(
            [
                100.0,
                110.0,
                120.0,
            ]
        )
    )

    for strategy in result.results:
        assert (
            strategy.observations[0]
            .forward_return_percent
            == pytest.approx(10.0)
        )


def test_research_is_deterministic():

    data = _data()

    research = RegimeStrategyResearch()

    first = research.run(data)
    second = research.run(data)

    assert first == second
