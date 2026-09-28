from atlas.market.asset_type import AssetType
from atlas.market.asset_universe import AssetUniverse
from atlas.market.broad_asset_provider import BroadAssetProvider


class FakeInstrumentSource:
    def list_instruments(self):
        return [
            {
                "symbol": "PLTR",
                "name": "Palantir Technologies",
                "type": "EQUITY",
                "market": "US",
                "currency": "USD",
                "active": True,
            },
            {
                "symbol": "SOL-USD",
                "name": "Solana",
                "type": "CRYPTOCURRENCY",
                "market": "crypto",
                "currency": "USD",
                "active": True,
            },
            {
                "symbol": "UNKNOWN",
                "name": "Unsupported",
                "type": "BOND",
                "market": "US",
                "currency": "USD",
                "active": True,
            },
            {
                "symbol": "OLD",
                "name": "Inactive",
                "type": "EQUITY",
                "market": "US",
                "currency": "USD",
                "active": False,
            },
            {
                "symbol": "AMD",
                "name": "Advanced Micro Devices",
                "type": "EQUITY",
                "market": "US",
                "currency": "USD",
                "active": True,
            },
        ]


def test_broad_asset_provider_normalizes_filters_and_limits_external_feed():
    provider = BroadAssetProvider(
        source=FakeInstrumentSource(),
        limit=2,
    )

    assets = provider.list_assets()

    assert [asset.symbol for asset in assets] == [
        "PLTR",
        "SOL-USD",
    ]
    assert assets[0].asset_type == AssetType.STOCK
    assert assets[1].asset_type == AssetType.CRYPTO


def test_broad_asset_provider_plugs_into_existing_asset_universe_contract():
    universe = AssetUniverse(
        provider=BroadAssetProvider(
            source=FakeInstrumentSource(),
            limit=2,
        )
    )

    assert universe.symbols() == ["PLTR", "SOL-USD"]
