from datetime import datetime, timedelta, timezone

import pytest

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
    OHLCVBar,
)
from atlas.trading.opening_range_research import (
    OpeningRangeResearch,
)


def _bar(timestamp, *, open_, high, low, close):
    return OHLCVBar(
        timestamp=timestamp,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=1000.0,
    )


def test_measures_us_opening_range_without_creating_trading_action():
    # 2026-01-15: New York is UTC-5.
    # 14:30 UTC == 09:30 New York.
    start = datetime(2026, 1, 15, 14, 15, tzinfo=timezone.utc)

    bars = [
        _bar(
            start,
            open_=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
        ),
        _bar(
            start + timedelta(minutes=5),
            open_=100.0,
            high=102.0,
            low=99.0,
            close=101.0,
        ),
        _bar(
            start + timedelta(minutes=10),
            open_=101.0,
            high=102.0,
            low=100.0,
            close=101.0,
        ),
        # 09:30-09:45 New York opening range.
        _bar(
            start + timedelta(minutes=15),
            open_=101.0,
            high=103.0,
            low=100.0,
            close=102.0,
        ),
        _bar(
            start + timedelta(minutes=20),
            open_=102.0,
            high=105.0,
            low=101.0,
            close=104.0,
        ),
        _bar(
            start + timedelta(minutes=25),
            open_=104.0,
            high=106.0,
            low=102.0,
            close=105.0,
        ),
        # First close after the completed opening range.
        _bar(
            start + timedelta(minutes=30),
            open_=105.0,
            high=108.0,
            low=104.0,
            close=107.0,
        ),
    ]

    data = HistoricalMarketData(
        symbol="BTCUSDT",
        timeframe="5m",
        source="test",
        bars=bars,
    )

    result = OpeningRangeResearch(
        opening_minutes=15,
        reference_minutes=15,
        forward_period=1,
    ).run(data)

    assert result.symbol == "BTCUSDT"
    assert result.timeframe == "5m"
    assert len(result.observations) == 1

    observation = result.observations[0]

    # Opening range: 106 - 100 = 6.
    # Normalize against the 09:30 opening price: 101.
    assert observation.opening_range_percent == pytest.approx(
        6.0 / 101.0 * 100.0
    )

    # Pre-open reference range: 102 - 99 = 3.
    # Normalize against the first reference-bar open: 100.
    assert observation.reference_range_percent == pytest.approx(
        3.0 / 100.0 * 100.0
    )

    # Compare absolute ranges, avoiding price-normalization distortion
    # inside the same short session window.
    assert observation.range_expansion_ratio == pytest.approx(2.0)

    # Evidence is complete at 09:45 New York.
    assert observation.available_at == datetime(
        2026, 1, 15, 14, 45, tzinfo=timezone.utc
    )

    # At 09:45 the completed opening-range candle closes at 105.
    # One 5m forward period therefore measures 105 -> 107.
    assert observation.forward_return_percent == pytest.approx(
        (107.0 / 105.0 - 1.0) * 100.0
    )

    assert not hasattr(observation, "action")
    assert not hasattr(observation, "decision")
    assert not hasattr(result, "action")
    assert not hasattr(result, "decision")


def test_opening_range_is_dst_aware():
    # 2026-07-15: New York is UTC-4.
    start = datetime(2026, 7, 15, 13, 15, tzinfo=timezone.utc)

    bars = [
        _bar(
            start + timedelta(minutes=5 * index),
            open_=100.0,
            high=101.0 + index,
            low=99.0,
            close=100.0 + index,
        )
        for index in range(7)
    ]

    data = HistoricalMarketData(
        symbol="BTCUSDT",
        timeframe="5m",
        source="test",
        bars=bars,
    )

    result = OpeningRangeResearch(
        opening_minutes=15,
        reference_minutes=15,
        forward_period=1,
    ).run(data)

    assert len(result.observations) == 1
    assert result.observations[0].available_at == datetime(
        2026, 7, 15, 13, 45, tzinfo=timezone.utc
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"opening_minutes": 0},
        {"reference_minutes": 0},
        {"forward_period": 0},
    ],
)
def test_research_parameters_must_be_positive(kwargs):
    with pytest.raises(ValueError):
        OpeningRangeResearch(**kwargs)


def test_incomplete_opening_range_is_skipped():
    # Missing the 09:35 New York candle.
    start = datetime(2026, 1, 15, 14, 15, tzinfo=timezone.utc)

    offsets = [
        0,
        5,
        10,
        15,  # 09:30
        25,  # 09:40 -- 09:35 is missing
        30,
        35,
    ]

    bars = [
        _bar(
            start + timedelta(minutes=offset),
            open_=100.0,
            high=102.0,
            low=99.0,
            close=101.0,
        )
        for offset in offsets
    ]

    data = HistoricalMarketData(
        symbol="BTCUSDT",
        timeframe="5m",
        source="test",
        bars=bars,
    )

    result = OpeningRangeResearch(
        opening_minutes=15,
        reference_minutes=15,
        forward_period=1,
    ).run(data)

    assert result.observations == ()


def test_incomplete_reference_range_is_skipped():
    # Missing the 09:20 New York reference candle.
    start = datetime(2026, 1, 15, 14, 15, tzinfo=timezone.utc)

    offsets = [
        0,   # 09:15
        10,  # 09:25 -- 09:20 is missing
        15,  # 09:30
        20,
        25,
        30,
    ]

    bars = [
        _bar(
            start + timedelta(minutes=offset),
            open_=100.0,
            high=102.0,
            low=99.0,
            close=101.0,
        )
        for offset in offsets
    ]

    data = HistoricalMarketData(
        symbol="BTCUSDT",
        timeframe="5m",
        source="test",
        bars=bars,
    )

    result = OpeningRangeResearch(
        opening_minutes=15,
        reference_minutes=15,
        forward_period=1,
    ).run(data)

    assert result.observations == ()
