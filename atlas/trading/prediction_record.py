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
    database_id: int | None = None
    analysis_snapshot_id: int | None = None
    analysts: list[str] = field(default_factory=list)
    reason: str = ""
    features: dict[str, float] = field(
        default_factory=dict
    )

    # Outcome fields are populated after the prediction
    # has been evaluated.
    evaluated: bool = False
    correct: bool | None = None
    evaluated_price_usd: float | None = None
    price_change_percent: float | None = None
    evaluated_at: datetime | None = None

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
            "analysis_snapshot_id": self.analysis_snapshot_id,
            "analysts": self.analysts,
            "reason": self.reason,
            "features": self.features,
            "evaluated": self.evaluated,
            "correct": self.correct,
            "evaluated_price_usd": (
                round(self.evaluated_price_usd, 2)
                if self.evaluated_price_usd is not None
                else None
            ),
            "price_change_percent": (
                round(self.price_change_percent, 2)
                if self.price_change_percent is not None
                else None
            ),
            "evaluated_at": (
                self.evaluated_at.isoformat(
                    timespec="seconds"
                )
                if self.evaluated_at is not None
                else None
            ),
        }
