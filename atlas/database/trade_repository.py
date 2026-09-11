"""
ATLAS paper trade persistence.

Persistence only. Trade lifecycle remains owned by TradingService.
"""

from datetime import datetime

from atlas.database.connection import Database
from atlas.trading.trade_record import TradeRecord


class TradeRepository:
    """Persist and load paper-trading history."""

    def __init__(self, database: Database):
        self.database = database

    def load(self):
        """Return persisted trades in chronological order."""

        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    symbol,
                    action,
                    quantity,
                    price_usd,
                    amount_nok,
                    realized_pnl_nok,
                    timestamp,
                    reason,
                    analysis_snapshot_id
                FROM paper_trades
                ORDER BY id
                """
            ).fetchall()

        return [
            TradeRecord(
                symbol=row["symbol"],
                action=row["action"],
                quantity=float(row["quantity"]),
                price_usd=float(row["price_usd"]),
                amount_nok=float(row["amount_nok"]),
                realized_pnl_nok=float(row["realized_pnl_nok"]),
                timestamp=datetime.fromisoformat(row["timestamp"]),
                reason=row["reason"],
                analysis_snapshot_id=row["analysis_snapshot_id"],
            )
            for row in rows
        ]

    def save(self, trade):
        """Persist one trade."""

        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO paper_trades (
                    symbol,
                    action,
                    quantity,
                    price_usd,
                    amount_nok,
                    realized_pnl_nok,
                    timestamp,
                    reason,
                    analysis_snapshot_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade.symbol,
                    trade.action,
                    float(trade.quantity),
                    float(trade.price_usd),
                    float(trade.amount_nok),
                    float(trade.realized_pnl_nok),
                    trade.timestamp.isoformat(),
                    trade.reason,
                    trade.analysis_snapshot_id,
                ),
            )
            connection.commit()

    def clear(self):
        """Remove all persisted trades."""

        with self.database.connect() as connection:
            connection.execute("DELETE FROM paper_trades")
            connection.commit()
