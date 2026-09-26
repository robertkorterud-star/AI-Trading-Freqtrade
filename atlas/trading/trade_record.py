"""
ATLAS Trade Record

Represents one completed paper-trading transaction.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class TradeRecord:
    """One paper-trading transaction."""

    symbol: str
    action: str
    quantity: float
    price_usd: float
    amount_nok: float
    realized_pnl_nok: float
    timestamp: datetime
    reason: str = ""
    analysis_snapshot_id: int | None = None

    def as_dict(self):
        return {
            "symbol": self.symbol,
            "action": self.action,
            "quantity": round(self.quantity, 8),
            "price_usd": round(self.price_usd, 2),
            "amount_nok": round(self.amount_nok, 2),
            "realized_pnl_nok": round(
                self.realized_pnl_nok,
                2,
            ),
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
            "analysis_snapshot_id": self.analysis_snapshot_id,
        }
