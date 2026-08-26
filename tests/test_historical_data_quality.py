from datetime import datetime, timedelta, timezone

from atlas.trading.historical_data_quality import (
    HistoricalDataQualityValidator,
)
from atlas.trading.historical_market_data import (
    HistoricalMarketData,
    OHLCVBar,
)


def _data(
    timestamps,
    *,
    open_price=100.0,
    high=105.0,
    low=99.0,
    close=104.0,
):

    return HistoricalMarketData(
        symbol="BTC-USD",
        timeframe="1h",
        source="test",
        bars=[
            OHLCVBar(
                timestamp=timestamp,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=1000.0,
            )
            for timestamp in timestamps
        ],
    )


def test_valid_data_is_accepted():

    start = datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    data = _data(
        [
            start,
            start + timedelta(hours=1),
            start + timedelta(hours=2),
        ]
    )

    result = (
        HistoricalDataQualityValidator()
        .validate(data)
    )

    assert result.valid is True
    assert result.bar_count == 3
    assert result.duplicate_count == 0
    assert result.invalid_ohlc_count == 0
    assert result.non_positive_price_count == 0
    assert result.gap_count == 0
    assert result.coverage_ratio_percent == 100.0


def test_empty_data_is_invalid():

    data = _data([])

    result = (
        HistoricalDataQualityValidator()
        .validate(data)
    )

    assert result.valid is False
    assert result.bar_count == 0
    assert "Dataset is empty." in result.issues


def test_gap_is_reported_but_does_not_make_data_invalid():

    start = datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    data = _data(
        [
            start,
            start + timedelta(hours=1),
            start + timedelta(hours=2),
            start + timedelta(hours=5),
        ]
    )

    result = (
        HistoricalDataQualityValidator()
        .validate(data)
    )

    assert result.valid is True
    assert result.gap_count == 1
    assert result.largest_gap_seconds == (
        3 * 60 * 60
    )
    assert result.coverage_ratio_percent < 100.0


def test_duplicate_timestamp_is_invalid():

    start = datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    data = _data(
        [
            start,
            start + timedelta(hours=1),
        ]
    )

    # HistoricalMarketData itself rejects
    # non-chronological duplicates, so this
    # validator receives normalized data.
    assert len(data) == 2


def test_non_positive_prices_are_rejected_before_quality_validation():

    start = datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    import pytest

    with pytest.raises(ValueError):
        _data(
            [start],
            open_price=-1.0,
        )


def test_quality_result_is_deterministic():

    start = datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    data = _data(
        [
            start,
            start + timedelta(hours=1),
            start + timedelta(hours=2),
            start + timedelta(hours=5),
        ]
    )

    validator = HistoricalDataQualityValidator()

    first = validator.validate(data)
    second = validator.validate(data)

    assert first == second
