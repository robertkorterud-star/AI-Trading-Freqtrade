from datetime import datetime, timedelta, timezone

import pytest

from atlas.trading.historical_market_data import HistoricalMarketData, OHLCVBar
from atlas.trading.news_event_research import NewsEventResearch


START = datetime(2026, 1, 2, 12, tzinfo=timezone.utc)


def market_data(minutes, prices):
    return HistoricalMarketData(
        symbol="BTCUSDT", timeframe="5m", source="test",
        bars=[OHLCVBar(START + timedelta(minutes=m), p, p, p, p, 100)
              for m, p in zip(minutes, prices)],
    )


def test_news_mid_candle_uses_next_open_and_real_elapsed_time():
    data = market_data([0, 5, 10, 20, 65], [100, 105, 110, 121, 132])
    result = NewsEventResearch(horizons=(timedelta(minutes=15), timedelta(hours=1))).run(
        data=data, articles=[{"title": "Event", "published_at": "2026-01-02T12:02:00Z"}],
    )
    event = result.observations[0]
    assert event.entry_timestamp == START + timedelta(minutes=5)
    assert event.entry_price == 105
    assert event.returns[0].observed_timestamp == START + timedelta(minutes=20)
    assert event.returns[0].return_percent == pytest.approx((121 / 105 - 1) * 100)
    assert event.returns[1].return_percent == pytest.approx((132 / 105 - 1) * 100)
    assert not hasattr(event, "action")
    assert not hasattr(result, "decision")


def test_market_closed_uses_next_open_and_reports_missing_horizon():
    data = market_data([0, 3 * 24 * 60, 3 * 24 * 60 + 60], [100, 110, 120])
    result = NewsEventResearch(horizons=(timedelta(hours=1), timedelta(days=7))).run(
        data=data, articles=[{"published_at": START + timedelta(hours=2)}],
    )
    event = result.observations[0]
    assert event.entry_timestamp == START + timedelta(days=3)
    assert event.returns[0].return_percent == pytest.approx((120 / 110 - 1) * 100)
    assert event.returns[1].return_percent is None
    assert event.returns[1].observed_timestamp is None


def test_invalid_news_is_skipped_and_missing_entry_is_skipped():
    result = NewsEventResearch().run(
        data=market_data([0, 5], [100, 110]),
        articles=[{"published_at": "bad"}, {"published_at": "2026-01-02T12:03:00"},
                  {"published_at": "2026-01-03T12:00:00Z"}],
    )
    assert result.observations == ()


def test_rejects_ambiguous_bar_timestamps():
    naive = HistoricalMarketData("BTCUSDT", [OHLCVBar(datetime(2026, 1, 1), 1, 1, 1, 1, 1)])
    with pytest.raises(ValueError, match="timezone-aware"):
        NewsEventResearch().run(data=naive, articles=[])


def test_horizons_must_be_positive():
    with pytest.raises(ValueError, match="positive"):
        NewsEventResearch(horizons=(timedelta(0),))
