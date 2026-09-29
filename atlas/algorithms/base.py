"""ATLAS algorithmic trading contracts."""

from dataclasses import dataclass, field
from typing import Protocol

from atlas.models.action import Action


@dataclass(frozen=True, slots=True)
class AlgorithmSignal:
    """Structured output produced by a trading algorithm."""

    algorithm: str
    symbol: str
    timeframe: str
    action: Action
    score: float
    confidence: float
    expected_edge: float | None = None
    reasoning: list[str] = field(default_factory=list)
    evidence_family: str | None = None

    def as_dict(self) -> dict:
        """Return a JSON-friendly representation of the signal."""

        return {
            "algorithm": self.algorithm,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "action": self.action.value,
            "score": self.score,
            "confidence": self.confidence,
            "expected_edge": self.expected_edge,
            "reasoning": list(self.reasoning),
            "evidence_family": self.evidence_family,
        }


class TradingAlgorithm(Protocol):
    """Contract shared by all ATLAS trading algorithms."""

    name: str
    timeframe: str

    def generate_signal(
        self,
        symbol: str,
        candles: list[dict],
    ) -> AlgorithmSignal:
        """Generate a structured signal from historical candles."""
