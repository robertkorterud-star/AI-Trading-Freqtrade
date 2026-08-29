"""
ATLAS Market Intelligence.

Combines observations from independent agents without directly
creating buy/sell orders.
"""

from __future__ import annotations

from dataclasses import dataclass

from atlas.agents.base import AgentObservation


@dataclass(frozen=True, slots=True)
class IntelligenceResult:
    """Aggregated intelligence available to the decision layer."""

    symbol: str
    score: float
    confidence: float
    direction: str
    observations: tuple[AgentObservation, ...]

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "score": self.score,
            "confidence": self.confidence,
            "direction": self.direction,
            "observations": [
                observation.as_dict()
                for observation in self.observations
            ],
        }


class MarketIntelligence:
    """
    Aggregates independent agent observations.

    Scores are weighted by confidence. Conflicting observations
    naturally reduce the aggregate score.
    """

    def analyze(
        self,
        symbol: str,
        observations: list[AgentObservation],
    ) -> IntelligenceResult:
        if not observations:
            return IntelligenceResult(
                symbol=symbol,
                score=0.0,
                confidence=0.0,
                direction="neutral",
                observations=(),
            )

        weighted_score = 0.0
        confidence_weight = 0.0

        for observation in observations:
            confidence = self._clamp(observation.confidence)
            score = self._clamp_signed(observation.score)

            weighted_score += score * confidence
            confidence_weight += confidence

        if confidence_weight <= 0.0:
            score = 0.0
            confidence = 0.0
        else:
            score = weighted_score / confidence_weight
            confidence = min(
                1.0,
                confidence_weight / len(observations),
            )

        if score > 0.20:
            direction = "bullish"
        elif score < -0.20:
            direction = "bearish"
        else:
            direction = "neutral"

        return IntelligenceResult(
            symbol=symbol,
            score=score,
            confidence=confidence,
            direction=direction,
            observations=tuple(observations),
        )

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    @staticmethod
    def _clamp_signed(value: float) -> float:
        return max(-1.0, min(1.0, value))
