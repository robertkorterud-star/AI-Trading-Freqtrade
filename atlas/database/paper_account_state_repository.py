"""Persistent paper-account state.

Stores durable account-level state that cannot be reconstructed from the
paper-trade ledger alone.
"""

from atlas.database.connection import Database


class PaperAccountStateRepository:
    """Persist durable paper-account state."""

    def __init__(self, database: Database):
        self.database = database

    def get_peak_equity_nok(self):
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT peak_equity_nok FROM paper_account_state WHERE id = 1"
            ).fetchone()

        if row is None or row["peak_equity_nok"] is None:
            return None

        return float(row["peak_equity_nok"])

    def set_peak_equity_nok(self, peak_equity_nok):
        value = float(peak_equity_nok)

        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO paper_account_state (id, peak_equity_nok)
                VALUES (1, ?)
                ON CONFLICT(id) DO UPDATE SET
                    peak_equity_nok = excluded.peak_equity_nok
                """,
                (value,),
            )
            connection.commit()
