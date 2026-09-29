"""Persistent asset catalogue for ATLAS."""

from atlas.database.connection import Database
from atlas.market.asset import Asset
from atlas.market.asset_type import AssetType


class AssetRepository:
    """Store and retrieve assets discovered by ATLAS."""

    def __init__(self, database: Database):
        self.database = database

    def save(self, asset: Asset) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO assets (
                    symbol,
                    name,
                    asset_type,
                    market,
                    currency,
                    active
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    name = excluded.name,
                    asset_type = excluded.asset_type,
                    market = excluded.market,
                    currency = excluded.currency,
                    active = excluded.active
                """,
                (
                    asset.symbol,
                    asset.name,
                    asset.asset_type.value,
                    asset.market,
                    asset.currency,
                    int(asset.active),
                ),
            )
            connection.commit()

    def get_all(self) -> tuple[Asset, ...]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    symbol,
                    name,
                    asset_type,
                    market,
                    currency,
                    active
                FROM assets
                ORDER BY symbol
                """
            ).fetchall()

        return tuple(
            Asset(
                symbol=row["symbol"],
                name=row["name"],
                asset_type=AssetType(row["asset_type"]),
                market=row["market"],
                currency=row["currency"],
                active=bool(row["active"]),
            )
            for row in rows
        )
