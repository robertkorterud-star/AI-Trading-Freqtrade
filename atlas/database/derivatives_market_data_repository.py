"""Persistent storage for normalized ATLAS derivatives market data."""

from datetime import datetime

from atlas.database.connection import Database
from atlas.trading.historical_derivatives_data import (
    FundingRateObservation,
    OpenInterestObservation,
)


class DerivativesMarketDataRepository:
    """Store and retrieve normalized historical derivatives observations."""

    def __init__(self, database: Database):
        self.database = database

    def save_funding_rates(
        self,
        symbol: str,
        source: str,
        observations,
    ) -> None:
        rows = [
            (
                source,
                symbol,
                observation.timestamp.isoformat(),
                observation.funding_rate,
                observation.mark_price,
            )
            for observation in observations
        ]

        if not rows:
            return

        with self.database.connect() as connection:
            connection.executemany(
                """
                INSERT INTO historical_funding_rates (
                    source,
                    symbol,
                    timestamp,
                    funding_rate,
                    mark_price
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source, symbol, timestamp)
                DO UPDATE SET
                    funding_rate = excluded.funding_rate,
                    mark_price = excluded.mark_price
                """,
                rows,
            )
            connection.commit()

    def load_funding_rates(
        self,
        symbol: str,
        source: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> tuple[FundingRateObservation, ...]:
        clauses = ["source = ?", "symbol = ?"]
        parameters = [source, symbol]

        if start is not None:
            clauses.append("timestamp >= ?")
            parameters.append(start.isoformat())

        if end is not None:
            clauses.append("timestamp < ?")
            parameters.append(end.isoformat())

        query = f"""
            SELECT timestamp, funding_rate, mark_price
            FROM historical_funding_rates
            WHERE {" AND ".join(clauses)}
            ORDER BY timestamp ASC
        """

        with self.database.connect() as connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return tuple(
            FundingRateObservation(
                timestamp=datetime.fromisoformat(row["timestamp"]),
                funding_rate=float(row["funding_rate"]),
                mark_price=float(row["mark_price"]),
            )
            for row in rows
        )

    def save_open_interest(
        self,
        symbol: str,
        source: str,
        period: str,
        observations,
    ) -> None:
        rows = [
            (
                source,
                symbol,
                period,
                observation.timestamp.isoformat(),
                observation.open_interest,
                observation.open_interest_value,
            )
            for observation in observations
        ]

        if not rows:
            return

        with self.database.connect() as connection:
            connection.executemany(
                """
                INSERT INTO historical_open_interest (
                    source,
                    symbol,
                    period,
                    timestamp,
                    open_interest,
                    open_interest_value
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, symbol, period, timestamp)
                DO UPDATE SET
                    open_interest = excluded.open_interest,
                    open_interest_value = excluded.open_interest_value
                """,
                rows,
            )
            connection.commit()

    def load_open_interest(
        self,
        symbol: str,
        source: str,
        period: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> tuple[OpenInterestObservation, ...]:
        clauses = [
            "source = ?",
            "symbol = ?",
            "period = ?",
        ]
        parameters = [source, symbol, period]

        if start is not None:
            clauses.append("timestamp >= ?")
            parameters.append(start.isoformat())

        if end is not None:
            clauses.append("timestamp < ?")
            parameters.append(end.isoformat())

        query = f"""
            SELECT timestamp, open_interest, open_interest_value
            FROM historical_open_interest
            WHERE {" AND ".join(clauses)}
            ORDER BY timestamp ASC
        """

        with self.database.connect() as connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return tuple(
            OpenInterestObservation(
                timestamp=datetime.fromisoformat(row["timestamp"]),
                open_interest=float(row["open_interest"]),
                open_interest_value=float(
                    row["open_interest_value"]
                ),
            )
            for row in rows
        )
