from datetime import datetime, timezone

from atlas.intelligence.market_session import (
    MarketSession,
    analyze_market_session,
)


def test_us_open_is_dst_aware_in_winter():
    result = analyze_market_session(
        datetime(2026, 1, 15, 14, 30, tzinfo=timezone.utc)
    )

    assert isinstance(result, MarketSession)
    assert result.us_market_open is True
    assert result.new_york_time.hour == 9
    assert result.new_york_time.minute == 30
    assert result.session == "US_OPEN"


def test_us_open_is_dst_aware_in_summer():
    result = analyze_market_session(
        datetime(2026, 7, 15, 13, 30, tzinfo=timezone.utc)
    )

    assert result.us_market_open is True
    assert result.new_york_time.hour == 9
    assert result.new_york_time.minute == 30
    assert result.session == "US_OPEN"


def test_same_utc_time_is_not_us_open_year_round():
    winter = analyze_market_session(
        datetime(2026, 1, 15, 13, 30, tzinfo=timezone.utc)
    )
    summer = analyze_market_session(
        datetime(2026, 7, 15, 13, 30, tzinfo=timezone.utc)
    )

    assert winter.us_market_open is False
    assert summer.us_market_open is True


def test_europe_us_overlap_is_descriptive_context():
    result = analyze_market_session(
        datetime(2026, 1, 15, 16, 0, tzinfo=timezone.utc)
    )

    assert result.europe_us_overlap is True
    assert result.session == "EUROPE_US_OVERLAP"

    # Session intelligence is context/evidence only.
    assert not hasattr(result, "action")
