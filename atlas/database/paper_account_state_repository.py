"""Persistent paper-account state.

Stores durable account-level state that cannot be reconstructed from the
paper-trade ledger alone.
"""

from datetime import datetime

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


    def get_trade_replay_after(self):
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT trade_replay_after FROM paper_account_state WHERE id = 1"
            ).fetchone()

        if row is None or row["trade_replay_after"] is None:
            return None

        return datetime.fromisoformat(row["trade_replay_after"])

    def set_trade_replay_after(self, timestamp):
        value = timestamp
        if isinstance(value, str):
            value = datetime.fromisoformat(value)

        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO paper_account_state (id, trade_replay_after)
                VALUES (1, ?)
                ON CONFLICT(id) DO UPDATE SET
                    trade_replay_after = excluded.trade_replay_after
                """,
                (value.isoformat(),),
            )
            connection.commit()

    def get_position_peak_price_usd(self, symbol):
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT peak_price_usd FROM paper_position_state WHERE symbol = ?",
                (str(symbol),),
            ).fetchone()

        if row is None:
            return None

        return float(row["peak_price_usd"])

    def get_position_peak_symbols(self):
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT symbol FROM paper_position_state"
            ).fetchall()

        return [str(row["symbol"]) for row in rows]

    def set_position_peak_price_usd(self, symbol, peak_price_usd):
        value = float(peak_price_usd)

        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO paper_position_state (symbol, peak_price_usd)
                VALUES (?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    peak_price_usd = excluded.peak_price_usd
                """,
                (str(symbol), value),
            )
            connection.commit()

    def delete_position_peak_price_usd(self, symbol):
        with self.database.connect() as connection:
            connection.execute(
                "DELETE FROM paper_position_state WHERE symbol = ?",
                (str(symbol),),
            )
            connection.commit()
