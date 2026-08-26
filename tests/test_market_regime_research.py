from datetime import datetime, timedelta, timezone

import pytest

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
    OHLCVBar,
)
from atlas.trading.market_regime_research import (
    MarketRegimeResearch,
)


def _data(
    closes: list[float] | None = None,
) -> HistoricalMarketData:

    if closes is None:
        closes = [
            100.0 + index
            for index in range(120)
        ]

    start = datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    bars = []

    for index, close in enumerate(closes):
        bars.append(
            OHLCVBar(
                timestamp=(
                    start
                    + timedelta(hours=index)
                ),
                open=close - 0.5,
                high=close + 1.0,
                low=close - 1.0,
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


def test_market_regime_research_runs():

    result = MarketRegimeResearch().run(
        _data()
    )

    assert result.symbol == "BTC-USD"
    assert result.timeframe == "4h"
    assert result.source == "test"
    assert len(result.observations) == 119
    assert result.classified_observations > 0


def test_forward_period_must_be_positive():

    with pytest.raises(ValueError):

        MarketRegimeResearch(
            forward_period=0,
        )


def test_forward_return_uses_future_candle():

    data = _data(
        [
            100.0,
            110.0,
            120.0,
        ]
    )

    result = MarketRegimeResearch(
        forward_period=1,
    ).run(data)

    assert (
        result.observations[0]
        .forward_return_percent
        == pytest.approx(10.0)
    )

    assert (
        result.observations[1]
        .forward_return_percent
        == (
            (120.0 / 110.0 - 1.0)
            * 100.0
        )
    )


def test_last_observation_has_no_forward_return():

    result = MarketRegimeResearch().run(
        _data()
    )

    # The final candle cannot be used as a
    # classified observation because there is
    # no future candle available.
    assert all(
        observation.forward_return_percent
        is not None
        for observation in result.observations
    )


def test_regime_distribution_is_deterministic():

    data = _data()

    first = MarketRegimeResearch().run(
        data
    )

    second = MarketRegimeResearch().run(
        data
    )

    assert first == second
    assert (
        first.regime_distribution
        == second.regime_distribution
    )


def test_short_dataset_is_safe():

    data = _data(
        [
            100.0,
        ]
    )

    result = MarketRegimeResearch().run(
        data
    )

    assert result.observations == ()
    assert result.classified_observations == 0
