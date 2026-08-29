"""
ATLAS Agent Intelligence Contracts.

Agents observe and interpret market information.
They do not execute trades.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AgentObservation:
    """Normalized observation produced by an ATLAS agent."""

    agent: str
    symbol: str
    timestamp: str | None = None
    category: str = "general"
    score: float = 0.0
    confidence: float = 0.0
    direction: str = "neutral"
    reason: str | None = None
    source: str | None = None
    features: dict[str, float] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "agent": self.agent,
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "category": self.category,
            "score": self.score,
            "confidence": self.confidence,
            "direction": self.direction,
            "reason": self.reason,
            "source": self.source,
            "features": dict(self.features),
            "evidence": list(self.evidence),
        }


class MarketAgent(Protocol):
    """Contract implemented by market-intelligence agents."""

    name: str
    category: str

    def observe(
        self,
        symbol: str,
        market_data: dict,
    ) -> AgentObservation:
        """Produce an observation from market information."""
