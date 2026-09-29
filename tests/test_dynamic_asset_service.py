from atlas.market.asset import Asset
from atlas.market.asset_type import AssetType
from atlas.market.asset_universe import AssetUniverse
from atlas.services.dynamic_asset_service import (
    DynamicAssetService,
)


class FakeResolver:
    def resolve(self, query):
        return [
            Asset(
                symbol="PLTR",
                name="Palantir Technologies Inc.",
                asset_type=AssetType.STOCK,
                market="NMS",
                currency="USD",
            )
        ]


def test_dynamic_asset_service_adds_resolved_assets():

    universe = AssetUniverse(
        assets=[]
    )

    service = DynamicAssetService(
        resolver=FakeResolver(),
        universe=universe,
    )

    added = service.resolve_and_add(
        "Palantir"
    )

    assert added == 1
    assert universe.get("PLTR") is not None
    assert universe.get("PLTR").asset_type == (
        AssetType.STOCK
    )


def test_dynamic_asset_service_adds_only_exact_symbol_for_known_ticker():
    class BroadResolver:
        def resolve(self, query):
            assert query == "IEX"
            return [
                Asset(
                    symbol="IEX",
                    name="IDEX Corporation",
                    asset_type=AssetType.STOCK,
                    market="NYQ",
                    currency="USD",
                ),
                Asset(
                    symbol="IEX.NS",
                    name="Indian Energy Exchange Limited",
                    asset_type=AssetType.STOCK,
                    market="NSI",
                    currency="INR",
                ),
                Asset(
                    symbol="RLC-USD",
                    name="iExec RLC USD",
                    asset_type=AssetType.CRYPTO,
                    market="CCC",
                    currency="USD",
                ),
            ]

    universe = AssetUniverse(assets=[])
    service = DynamicAssetService(
        resolver=BroadResolver(),
        universe=universe,
    )

    added = service.resolve_and_add_symbol("IEX")

    assert added == 1
    assert universe.symbols() == ["IEX"]
