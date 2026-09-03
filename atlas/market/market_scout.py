"""
ATLAS Market Scout v1.

A deterministic, explainable pre-filter inspired by momentum stock scanners.
It does not place orders and does not depend on a specific market-data vendor.

The scout turns raw market observations into a ranked candidate list.  The
result is intentionally a *research signal*, not a trading decision.
"""

from dataclasses import dataclass, field
from enum import Enum


class AssetType(str, Enum):
    STOCK = "stock"
    CRYPTO = "crypto"


@dataclass(frozen=True, slots=True)
class MarketObservation:
    """Market snapshot consumed by the scout."""

    symbol: str
    asset_type: AssetType
    price: float
    volume: float
    average_volume: float
    change_percent: float = 0.0
    gap_percent: float = 0.0
    relative_volume_5m: float = 0.0
    float_shares: float | None = None
    atr_percent: float = 0.0
    news_catalyst: bool = False
    liquid: bool = True
    breakout_percent: float = 0.0


@dataclass(frozen=True, slots=True)
class ScoutEvidence:
    """Explainable scoring components for one market candidate."""

    symbol: str
    asset_type: AssetType
    score: float
    momentum_score: float
    volume_score: float
    breakout_score: float
    catalyst_score: float
    liquidity_score: float
    reasons: tuple[str, ...] = field(default_factory=tuple)


class MarketScout:
    """Rank market observations by observable momentum opportunity."""

    MIN_STOCK_PRICE = 1.0
    MIN_CRYPTO_PRICE = 0.0
    MIN_AVERAGE_VOLUME = 100_000.0
    MIN_VOLUME = 100_000.0

    def _eligible(self, observation: MarketObservation) -> bool:
        if not observation.symbol.strip():
            return False
        if observation.price <= (
            self.MIN_STOCK_PRICE
            if observation.asset_type is AssetType.STOCK
            else self.MIN_CRYPTO_PRICE
        ):
            return False
        if observation.average_volume < self.MIN_AVERAGE_VOLUME:
            return False
        if observation.volume < self.MIN_VOLUME:
            return False
        if not observation.liquid:
            return False
        return True

    @staticmethod
    def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
        return max(low, min(high, value))

    def _volume_ratio(self, observation: MarketObservation) -> float:
        if observation.average_volume <= 0:
            return 0.0
        return observation.volume / observation.average_volume

    def _momentum_score(self, observation: MarketObservation) -> float:
        # 10% daily move maps to 50; 20% maps to 100.
        return self._clamp(max(0.0, observation.change_percent) * 5.0)

    def _volume_score(self, observation: MarketObservation) -> float:
        # 5x average volume is the strong-demand reference point.
        ratio = self._volume_ratio(observation)
        return self._clamp(ratio * 20.0)

    def _breakout_score(self, observation: MarketObservation) -> float:
        # Gap/breakout distance and short-term relative volume approximate breakout pressure.
        price_breakout = max(0.0, observation.gap_percent, observation.breakout_percent) * 5.0
        short_volume = max(0.0, observation.relative_volume_5m) * 10.0
        return self._clamp(price_breakout + short_volume)

    @staticmethod
    def _catalyst_score(observation: MarketObservation) -> float:
        return 100.0 if observation.news_catalyst else 0.0

    def _liquidity_score(self, observation: MarketObservation) -> float:
        if not observation.liquid:
            return 0.0
        ratio = self._volume_ratio(observation)
        return self._clamp(50.0 + ratio * 10.0)

    def evidence(self, observation: MarketObservation) -> ScoutEvidence:
        """Build explainable evidence without making a BUY/SELL decision."""
        momentum = self._momentum_score(observation)
        volume = self._volume_score(observation)
        breakout = self._breakout_score(observation)
        catalyst = self._catalyst_score(observation)
        liquidity = self._liquidity_score(observation)

        # Momentum/volume lead because this is a discovery layer.
        score = round(
            self._clamp(
                momentum * 0.30
                + volume * 0.30
                + breakout * 0.20
                + catalyst * 0.10
                + liquidity * 0.10
            ),
            4,
        )

        reasons: list[str] = []
        if observation.change_percent >= 10.0:
            reasons.append("strong daily momentum")
        if self._volume_ratio(observation) >= 5.0:
            reasons.append("high relative volume")
        if observation.relative_volume_5m >= 5.0:
            reasons.append("high 5-minute relative volume")
        if max(observation.gap_percent, observation.breakout_percent) >= 5.0:
            reasons.append("breakout pressure")
        if observation.news_catalyst:
            reasons.append("news catalyst")
        if observation.float_shares is not None and observation.float_shares < 10_000_000:
            reasons.append("low float")

        return ScoutEvidence(
            symbol=observation.symbol,
            asset_type=observation.asset_type,
            score=score,
            momentum_score=round(momentum, 4),
            volume_score=round(volume, 4),
            breakout_score=round(breakout, 4),
            catalyst_score=round(catalyst, 4),
            liquidity_score=round(liquidity, 4),
            reasons=tuple(reasons),
        )

    def scan(self, observations: list[MarketObservation]) -> list[ScoutEvidence]:
        """Return eligible candidates, strongest first."""
        candidates = [
            self.evidence(observation)
            for observation in observations
            if self._eligible(observation)
        ]
        candidates.sort(key=lambda item: (item.score, item.symbol), reverse=True)
        return candidates
