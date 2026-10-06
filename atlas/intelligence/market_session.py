"""Market-session context for ATLAS.

Provides descriptive time/session evidence only.
This module never creates BUY, SELL or HOLD decisions.
"""

from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo


_NEW_YORK = ZoneInfo("America/New_York")
_LONDON = ZoneInfo("Europe/London")


@dataclass(frozen=True, slots=True)
class MarketSession:
    """Descriptive market-session context."""

    timestamp: datetime
    new_york_time: datetime
    london_time: datetime
    session: str
    us_market_open: bool
    europe_us_overlap: bool


def analyze_market_session(timestamp: datetime) -> MarketSession:
    """Classify session context for an aware market timestamp."""

    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")

    new_york_time = timestamp.astimezone(_NEW_YORK)
    london_time = timestamp.astimezone(_LONDON)

    ny_clock = new_york_time.time().replace(tzinfo=None)
    london_clock = london_time.time().replace(tzinfo=None)

    us_market_open = time(9, 30) <= ny_clock < time(10, 30)

    europe_open = time(8, 0) <= london_clock < time(16, 30)
    us_cash_session = time(9, 30) <= ny_clock < time(16, 0)

    europe_us_overlap = europe_open and us_cash_session

    if us_market_open:
        session = "US_OPEN"
    elif europe_us_overlap:
        session = "EUROPE_US_OVERLAP"
    elif us_cash_session:
        session = "US_SESSION"
    elif europe_open:
        session = "EUROPE"
    else:
        session = "OFF_HOURS"

    return MarketSession(
        timestamp=timestamp,
        new_york_time=new_york_time,
        london_time=london_time,
        session=session,
        us_market_open=us_market_open,
        europe_us_overlap=europe_us_overlap,
    )
