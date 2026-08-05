"""
Shared types used across the ATLAS engine.
"""

from dataclasses import dataclass
from enum import Enum


class Signal(str, Enum):
    """
    Standard trading signals.
    """

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(slots=True)
class AgentResult:
    """
    Standard response returned by every agent.
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