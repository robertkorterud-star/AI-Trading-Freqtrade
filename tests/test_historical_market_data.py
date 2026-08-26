from datetime import datetime, timedelta

import pytest

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
    OHLCVBar,
)


def _bars(count=5):

    start = datetime(
        2026,
        1,
        1,
    )

    return [
        OHLCVBar(
            timestamp=start + timedelta(
                days=index
            ),
            open=100.0 + index,
            high=105.0 + index,
            low=99.0 + index,
            close=104.0 + index,
            volume=1000.0 + index,
        )
        for index in range(count)
    ]


def test_historical_market_data_accepts_valid_bars():

    data = HistoricalMarketData(
        symbol="BTC-USD",
        bars=_bars(),
    )

    assert data.symbol == "BTC-USD"
    assert len(data) == 5
    assert len(data.bars) == 5


def test_closes_are_extracted_in_order():

    data = HistoricalMarketData(
        symbol="BTC-USD",
        bars=_bars(),
    )

    assert data.closes == [
        104.0,
        105.0,
        106.0,
        107.0,
        108.0,
    ]


def test_timestamps_are_extracted_in_order():

    data = HistoricalMarketData(
        symbol="BTC-USD",
        bars=_bars(),
    )

    assert data.timestamps == [
        bar.timestamp
        for bar in _bars()
    ]


def test_bars_are_immutable_from_public_property():

    data = HistoricalMarketData(
        symbol="BTC-USD",
        bars=_bars(),
    )

    assert isinstance(
        data.bars,
        tuple,
    )


def test_symbol_must_not_be_empty():

    with pytest.raises(ValueError):
        HistoricalMarketData(
            symbol="",
            bars=_bars(),
        )


def test_bars_must_be_chronological():

    bars = _bars()

    bars[2] = OHLCVBar(
        timestamp=bars[1].timestamp,
        open=102.0,
        high=107.0,
        low=101.0,
        close=106.0,
        volume=1000.0,
    )

    with pytest.raises(ValueError):
        HistoricalMarketData(
            symbol="BTC-USD",
            bars=bars,
        )


def test_prices_must_be_positive():

    bars = _bars()

    bars[2] = OHLCVBar(
        timestamp=bars[2].timestamp,
        open=0.0,
        high=107.0,
        low=101.0,
        close=106.0,
        volume=1000.0,
    )

    with pytest.raises(ValueError):
        HistoricalMarketData(
            symbol="BTC-USD",
            bars=bars,
        )


def test_volume_cannot_be_negative():

    bars = _bars()

    bars[2] = OHLCVBar(
        timestamp=bars[2].timestamp,
        open=102.0,
        high=107.0,
        low=101.0,
        close=106.0,
        volume=-1.0,
    )

    with pytest.raises(ValueError):
        HistoricalMarketData(
            symbol="BTC-USD",
            bars=bars,
        )


def test_high_must_contain_open_and_close():

    bars = _bars()

    bars[2] = OHLCVBar(
        timestamp=bars[2].timestamp,
        open=102.0,
        high=101.0,
        low=101.0,
        close=106.0,
        volume=1000.0,
    )

    with pytest.raises(ValueError):
        HistoricalMarketData(
            symbol="BTC-USD",
            bars=bars,
        )


def test_low_must_contain_open_and_close():

    bars = _bars()

    bars[2] = OHLCVBar(
        timestamp=bars[2].timestamp,
        open=102.0,
        high=107.0,
        low=107.0,
        close=106.0,
        volume=1000.0,
    )

    with pytest.raises(ValueError):
        HistoricalMarketData(
            symbol="BTC-USD",
            bars=bars,
        )


def test_empty_dataset_is_allowed():

    data = HistoricalMarketData(
        symbol="BTC-USD",
        bars=[],
    )

    assert len(data) == 0
    assert data.closes == []
    assert data.timestamps == []
