from atlas.core.config import AtlasConfig
from atlas.core.engine import AtlasEngine
from atlas.market.asset import Asset
from atlas.market.asset_type import AssetType


class _ExactResolver:
    def resolve(self, query):
        if str(query).strip().upper() != "AMZN":
            return []

        return [
            Asset(
                symbol="AMZN",
                name="Amazon.com, Inc.",
                asset_type=AssetType.STOCK,
                market="US",
                currency="USD",
            )
        ]


def test_discovered_asset_survives_engine_restart(tmp_path):
    database_path = tmp_path / "atlas.db"

    config = AtlasConfig(
        database_path=str(database_path),
    )

    first = AtlasEngine(config=config)
    first.dynamic_asset_service.resolver = _ExactResolver()

    assert first.asset_universe.get("AMZN") is None

    added = first.dynamic_asset_service.resolve_and_add_symbol(
        "AMZN"
    )

    assert added == 1
    assert first.asset_universe.get("AMZN") is not None

    restarted = AtlasEngine(config=config)

    assert restarted.asset_universe.get("AMZN") is not None
