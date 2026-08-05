"""
Shared data models used by all ATLAS agents.
"""

from dataclasses import dataclass
from enum import Enum


class Signal(str, Enum):
    """Trading signals returned by agents."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(slots=True)
class AgentResult:
    """
    Standard response returned by every ATLAS agent.
    """

    agent: str
    signal: Signal
    score: float
    confidence: float
    reason: str

    def __str__(self) -> str:
        return (
            f"{self.agent}: "
            f"{self.signal.value} "
            f"(score={self.score:.1f}, "
            f"confidence={self.confidence:.1f})"
        )