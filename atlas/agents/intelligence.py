"""
ATLAS Market Intelligence.

Aggregates observations from registered market-intelligence agents.
Agents observe markets; this layer combines their observations without
executing trades.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from atlas.agents.base import AgentObservation, MarketAgent


@dataclass(frozen=True, slots=True)
class IntelligenceResult:
    """Aggregated result produced by the market-intelligence layer."""

    symbol: str
    score: float
    confidence: float
    direction: str
    observations: tuple[AgentObservation, ...]

    @property
    def average_score(self) -> float:
        if not self.observations:
            return 0.0

        return sum(
            observation.score
            for observation in self.observations
        ) / len(self.observations)

    @property
    def average_confidence(self) -> float:
        if not self.observations:
            return 0.0

        return sum(
            observation.confidence
            for observation in self.observations
        ) / len(self.observations)

    @property
    def bullish_count(self) -> int:
        return sum(
            observation.direction == "bullish"
            for observation in self.observations
        )

    @property
    def bearish_count(self) -> int:
        return sum(
            observation.direction == "bearish"
            for observation in self.observations
        )

    @property
    def neutral_count(self) -> int:
        return sum(
            observation.direction == "neutral"
            for observation in self.observations
        )


class MarketIntelligence:
    """
    Aggregates independent agent observations.

    Supports both the original explicit-observation API:

        analyze(symbol, observations)

    and the agent-pipeline API:

        MarketIntelligence(agents).analyze(snapshot)
    """

    def __init__(self, agents=None):
        self.agents = tuple(agents or ())

    def analyze(self, symbol_or_snapshot, observations=None) -> IntelligenceResult:
        """
        Analyze either explicit observations or a market snapshot.

        The explicit-observation API is retained for backwards
        compatibility with the existing intelligence tests.
        """

        if observations is not None:
            return self._aggregate(
                symbol_or_snapshot,
                observations,
            )

        snapshot = symbol_or_snapshot

        generated = []

        for agent in self.agents:
            analyze = getattr(agent, "analyze", None)

            if analyze is not None:
                generated.append(analyze(snapshot))
                continue

            observe = getattr(agent, "observe", None)

            if observe is None:
                raise TypeError(
                    f"Agent {agent!r} must implement analyze() or observe()"
                )

            generated.append(
                observe(
                    snapshot.symbol,
                    {
                        "snapshot": snapshot,
                        "price": snapshot.price,
                        "candles": snapshot.candles,
                    },
                )
            )

        return self._aggregate(
            snapshot.symbol,
            generated,
        )

    @staticmethod
    def _aggregate(
        symbol: str,
        observations,
    ) -> IntelligenceResult:
        observations = tuple(observations)

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
            confidence = MarketIntelligence._clamp(
                observation.confidence
            )
            score = MarketIntelligence._clamp_signed(
                observation.score
            )

            weighted_score += score * confidence
            confidence_weight += confidence

        if confidence_weight <= 0.0:
            score = 0.0
        else:
            score = weighted_score / confidence_weight

        # Confidence describes the reliability of the observation,
        # not the magnitude of its directional score.
        #
        # A neutral market can therefore have high analytical
        # confidence even when score is close to zero.
        confidence = min(
            1.0,
            sum(
                MarketIntelligence._clamp(
                    observation.confidence
                )
                for observation in observations
            ) / len(observations),
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
            observations=observations,
        )

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    @staticmethod
    def _clamp_signed(value: float) -> float:
        return max(-1.0, min(1.0, value))

