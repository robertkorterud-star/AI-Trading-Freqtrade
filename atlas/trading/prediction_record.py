"""
ATLAS Prediction Record

Stores one AI prediction for future outcome tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class PredictionRecord:
    """One AI prediction."""

    symbol: str
    action: str
    confidence: float
    evidence: float
    price_usd: float
    timestamp: datetime
    analysts: list[str] = field(default_factory=list)
    reason: str = ""

    def as_dict(self):
        return {
            "symbol": self.symbol,
            "action": self.action,
            "confidence": round(self.confidence, 2),
            "evidence": round(self.evidence, 2),
            "price_usd": round(self.price_usd, 2),
            "timestamp": self.timestamp.isoformat(
                timespec="seconds"
            ),
            "analysts": self.analysts,
            "reason": self.reason,
        }
