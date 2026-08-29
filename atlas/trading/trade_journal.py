"""
ATLAS Trade Journal

Records every dry-run trade and the decision context that produced it.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class TradeRecord:
    """Immutable record of a simulated trade."""

    trade_id: int
    timestamp: str
    symbol: str
    action: str
    quantity: float
    price: float
    fee: float
    realized_pnl: float
    reason: str
    confidence: float
    risk_score: float
    equity_after: float


@dataclass
class TradeJournal:
    """In-memory journal for dry-run trades."""

    records: list[TradeRecord] = field(default_factory=list)

    def record(
        self,
        symbol: str,
        action: str,
        quantity: float,
        price: float,
        fee: float,
        realized_pnl: float,
        reason: str,
        confidence: float,
        risk_score: float,
        equity_after: float,
    ) -> TradeRecord:
        """Append a trade record."""

        record = TradeRecord(
            trade_id=len(self.records) + 1,
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=price,
            fee=fee,
            realized_pnl=realized_pnl,
            reason=reason,
            confidence=confidence,
            risk_score=risk_score,
            equity_after=equity_after,
        )

        self.records.append(record)

        return record

    @property
    def trade_count(self) -> int:
        return len(self.records)

    @property
    def total_realized_pnl(self) -> float:
        return sum(record.realized_pnl for record in self.records)

    def latest(self) -> TradeRecord | None:
        if not self.records:
            return None

        return self.records[-1]
