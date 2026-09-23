"""Non-decisional market context for ATLAS.

Provides shared session, volatility and liquidity context for opportunity
discovery and downstream intelligence. It does not create trade decisions.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from atlas.market.asset_type import AssetType


@dataclass(frozen=True, slots=True)
class MarketContext:
    """Normalized context describing the current market environment."""

    asset_type: AssetType
    session: str
    volatility_level: str
    liquidity_level: str
    timestamp: float


class MarketContextService:
    """Build shared market context without producing BUY/SELL decisions."""

    US_EASTERN = ZoneInfo("America/New_York")

    @staticmethod
    def _volatility_level(change_percent: float) -> str:
        change = abs(float(change_percent))
        if change >= 5.0:
            return "EXTREME"
        if change >= 2.0:
            return "HIGH"
        if change >= 0.75:
            return "NORMAL"
        return "LOW"

    @staticmethod
    def _liquidity_level(volume_ratio: float) -> str:
        ratio = float(volume_ratio)
        if ratio <= 0:
            return "UNKNOWN"
        if ratio >= 3.0:
            return "VERY_HIGH"
        if ratio >= 1.5:
            return "HIGH"
        if ratio >= 0.75:
            return "NORMAL"
        return "LOW"

    @classmethod
    def _us_session(cls, timestamp: float) -> str:
        local = datetime.fromtimestamp(
            float(timestamp),
            tz=timezone.utc,
        ).astimezone(cls.US_EASTERN)
        minutes = local.hour * 60 + local.minute

        if minutes < 4 * 60:
            return "CLOSED"
        if minutes < 9 * 60 + 30:
            return "PREMARKET"
        if minutes < 10 * 60:
            return "EARLY_SESSION"
        if minutes < 15 * 60:
            return "MID_SESSION"
        if minutes < 16 * 60:
            return "POWER_HOUR"
        if minutes < 20 * 60:
            return "AFTER_HOURS"
        return "CLOSED"

    @classmethod
    def session(
        cls,
        asset_type: AssetType,
        timestamp: float,
    ) -> str:
        """Return market session context; crypto remains continuously open."""
        if asset_type == AssetType.CRYPTO:
            return "CRYPTO_24_7"
        return cls._us_session(timestamp)

    @classmethod
    def build(
        cls,
        *,
        asset_type: AssetType,
        timestamp: float,
        change_percent: float,
        volume_ratio: float,
    ) -> MarketContext:
        """Build context from normalized market observations."""
        return MarketContext(
            asset_type=asset_type,
            session=cls.session(asset_type, timestamp),
            volatility_level=cls._volatility_level(change_percent),
            liquidity_level=cls._liquidity_level(volume_ratio),
            timestamp=float(timestamp),
        )
