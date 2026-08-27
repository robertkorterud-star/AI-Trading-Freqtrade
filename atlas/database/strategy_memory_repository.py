"""
ATLAS Strategy Memory Repository.

Persistent database access for strategy/regime research.
"""

from datetime import datetime

from atlas.database.connection import Database
from atlas.trading.strategy_memory import (
    StrategyMemoryRecord,
)


class StrategyMemoryRepository:
    """Stores and retrieves strategy memory records."""

    def __init__(self, database: Database):
        self.database = database

    def save(
        self,
        record: StrategyMemoryRecord,
    ):
        """
        Store a strategy memory record.

        The current record is updated in strategy_memory while
        every save is also preserved in strategy_memory_history.
        """

        recorded_at = record.updated_at.isoformat(
            timespec="seconds"
        )

        with self.database.connect() as connection:

            cursor = connection.execute(
                """
                INSERT INTO strategy_memory (
                    symbol,
                    regime,
                    strategy_name,
                    trade_count,
                    winning_trades,
                    losing_trades,
                    win_rate_percent,
                    average_trade_return_percent,
                    total_return_percent,
                    evidence_strength,
                    robust_winner,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(
                    symbol,
                    regime,
                    strategy_name
                )
                DO UPDATE SET
                    trade_count = excluded.trade_count,
                    winning_trades = excluded.winning_trades,
                    losing_trades = excluded.losing_trades,
                    win_rate_percent = excluded.win_rate_percent,
                    average_trade_return_percent =
                        excluded.average_trade_return_percent,
                    total_return_percent =
                        excluded.total_return_percent,
                    evidence_strength =
                        excluded.evidence_strength,
                    robust_winner =
                        excluded.robust_winner,
                    updated_at =
                        excluded.updated_at
                """,
                (
                    record.symbol,
                    record.regime,
                    record.strategy_name,
                    record.trade_count,
                    record.winning_trades,
                    record.losing_trades,
                    record.win_rate_percent,
                    record.average_trade_return_percent,
                    record.total_return_percent,
                    record.evidence_strength,
                    int(record.robust_winner),
                    recorded_at,
                ),
            )

            connection.execute(
                """
                INSERT INTO strategy_memory_history (
                    symbol,
                    regime,
                    strategy_name,
                    trade_count,
                    winning_trades,
                    losing_trades,
                    win_rate_percent,
                    average_trade_return_percent,
                    total_return_percent,
                    evidence_strength,
                    robust_winner,
                    recorded_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.symbol,
                    record.regime,
                    record.strategy_name,
                    record.trade_count,
                    record.winning_trades,
                    record.losing_trades,
                    record.win_rate_percent,
                    record.average_trade_return_percent,
                    record.total_return_percent,
                    record.evidence_strength,
                    int(record.robust_winner),
                    recorded_at,
                ),
            )

            connection.commit()

            return cursor.lastrowid

    def get(
        self,
        *,
        symbol: str,
        regime: str,
        strategy_name: str,
    ) -> StrategyMemoryRecord | None:

        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM strategy_memory
                WHERE symbol = ?
                  AND regime = ?
                  AND strategy_name = ?
                """,
                (
                    symbol,
                    regime,
                    strategy_name,
                ),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_record(row)

    def history(
        self,
        *,
        symbol: str,
        regime: str,
        strategy_name: str,
    ) -> tuple[StrategyMemoryRecord, ...]:

        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM strategy_memory_history
                WHERE symbol = ?
                  AND regime = ?
                  AND strategy_name = ?
                ORDER BY id
                """,
                (
                    symbol,
                    regime,
                    strategy_name,
                ),
            ).fetchall()

        return tuple(
            self._history_row_to_record(row)
            for row in rows
        )

    def history_count(self) -> int:

        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM strategy_memory_history
                """
            ).fetchone()

        return int(row["count"])

    def for_regime(
        self,
        *,
        symbol: str,
        regime: str,
    ) -> tuple[StrategyMemoryRecord, ...]:

        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM strategy_memory
                WHERE symbol = ?
                  AND regime = ?
                ORDER BY strategy_name
                """,
                (
                    symbol,
                    regime,
                ),
            ).fetchall()

        return tuple(
            self._row_to_record(row)
            for row in rows
        )

    def get_all(
        self,
    ) -> tuple[StrategyMemoryRecord, ...]:

        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM strategy_memory
                ORDER BY
                    symbol,
                    regime,
                    strategy_name
                """
            ).fetchall()

        return tuple(
            self._row_to_record(row)
            for row in rows
        )

    def count(self) -> int:

        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM strategy_memory
                """
            ).fetchone()

        return int(row["count"])

    def clear(self) -> None:

        with self.database.connect() as connection:
            connection.execute(
                "DELETE FROM strategy_memory"
            )
            connection.commit()

    @staticmethod
    def _row_to_record(row):
        return StrategyMemoryRecord(
            symbol=row["symbol"],
            regime=row["regime"],
            strategy_name=row["strategy_name"],
            trade_count=int(row["trade_count"]),
            winning_trades=int(row["winning_trades"]),
            losing_trades=int(row["losing_trades"]),
            win_rate_percent=float(
                row["win_rate_percent"]
            ),
            average_trade_return_percent=float(
                row["average_trade_return_percent"]
            ),
            total_return_percent=float(
                row["total_return_percent"]
            ),
            evidence_strength=row["evidence_strength"],
            robust_winner=bool(
                row["robust_winner"]
            ),
            updated_at=datetime.fromisoformat(
                row["updated_at"]
            ),
        )

    @staticmethod
    def _history_row_to_record(row):
        return StrategyMemoryRecord(
            symbol=row["symbol"],
            regime=row["regime"],
            strategy_name=row["strategy_name"],
            trade_count=int(row["trade_count"]),
            winning_trades=int(row["winning_trades"]),
            losing_trades=int(row["losing_trades"]),
            win_rate_percent=float(
                row["win_rate_percent"]
            ),
            average_trade_return_percent=float(
                row["average_trade_return_percent"]
            ),
            total_return_percent=float(
                row["total_return_percent"]
            ),
            evidence_strength=row["evidence_strength"],
            robust_winner=bool(
                row["robust_winner"]
            ),
            updated_at=datetime.fromisoformat(
                row["recorded_at"]
            ),
        )
