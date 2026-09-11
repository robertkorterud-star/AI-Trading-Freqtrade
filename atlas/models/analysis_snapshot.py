"""
ATLAS Analysis Snapshot

Persistent snapshot of the latest AI/analyst analysis.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class AnalysisSnapshot:
    database_id: int | None
    symbol: str
    timestamp: datetime
    provider: str
    model: str
    results: list[dict]
    decision: dict
    intelligence: dict
    decision_ref: object | None = None

    def as_dict(self):
        return {
            "database_id": self.database_id,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(
                timespec="seconds"
            ),
            "provider": self.provider,
            "model": self.model,
            "results": self.results,
            "decision": self.decision,
            "intelligence": self.intelligence,
        }
