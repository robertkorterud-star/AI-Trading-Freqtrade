"""Persistent storage for normalized ATLAS historical OHLCV data."""

from datetime import datetime

from atlas.database.connection import Database
from atlas.trading.historical_market_data import HistoricalMarketData, OHLCVBar


class HistoricalMarketDataRepository:
    """Store and retrieve canonical HistoricalMarketData in SQLite."""

    def __init__(self, database: Database):
        self.database = database

    def save(self, data: HistoricalMarketData) -> None:
        """Persist bars idempotently by their canonical market-data identity."""
        rows = [
            (
                data.source,
                data.symbol,
                data.timeframe,
                bar.timestamp.isoformat(),
                bar.open,
                bar.high,
                bar.low,
                bar.close,
                bar.volume,
            )
            for bar in data.bars
        ]
        if not rows:
            return

        with self.database.connect() as connection:
            connection.executemany(
                """
                INSERT INTO historical_market_data (
                    source, symbol, timeframe, timestamp,
                    open, high, low, close, volume
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, symbol, timeframe, timestamp)
                DO UPDATE SET
                    open = excluded.open,
                    high = excluded.high,
                    low = excluded.low,
                    close = excluded.close,
                    volume = excluded.volume
                """,
                rows,
            )
            connection.commit()

    def load(
        self,
        symbol: str,
        timeframe: str,
        source: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> HistoricalMarketData:
        """Load bars chronologically; start is inclusive and end is exclusive."""
        clauses = ["source = ?", "symbol = ?", "timeframe = ?"]
        parameters = [source, symbol, timeframe]

        if start is not None:
            clauses.append("timestamp >= ?")
            parameters.append(start.isoformat())
        if end is not None:
            clauses.append("timestamp < ?")
            parameters.append(end.isoformat())

        query = f"""
            SELECT timestamp, open, high, low, close, volume
            FROM historical_market_data
            WHERE {" AND ".join(clauses)}
            ORDER BY timestamp ASC
        """

        with self.database.connect() as connection:
            rows = connection.execute(query, parameters).fetchall()

        return HistoricalMarketData(
            symbol=symbol,
            timeframe=timeframe,
            source=source,
            bars=[
                OHLCVBar(
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
                for row in rows
            ],
        )
