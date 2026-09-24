"""Trading horizon context for ATLAS market analysis.

Horizons select market-data timeframes for analysis and ranking. They do not
produce trade directions or replace the canonical DecisionEngine.
"""

from enum import Enum


class TradingHorizon(str, Enum):
    """Supported ATLAS analysis horizons."""

    LONG_TERM = "long_term"
    SWING = "swing"
    SHORT_TERM = "short_term"
    DAY_TRADE = "day_trade"
    SCALP = "scalp"

    # Compatibility aliases for the legacy multi-horizon signal path.
    INTRADAY = DAY_TRADE
    POSITION = LONG_TERM


_TIMEFRAMES_BY_HORIZON = {
    TradingHorizon.LONG_TERM: ("1wk", "1d"),
    TradingHorizon.SWING: ("1d", "1h"),
    TradingHorizon.SHORT_TERM: ("1d", "1h", "15m"),
    TradingHorizon.DAY_TRADE: ("1h", "15m", "5m"),
    TradingHorizon.SCALP: ("15m", "5m", "1m"),
}


def timeframes_for_horizon(
    horizon: TradingHorizon,
) -> tuple[str, ...]:
    """Return market-data timeframes used as context for a horizon."""
    return _TIMEFRAMES_BY_HORIZON[horizon]
