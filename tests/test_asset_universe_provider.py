from atlas.market.asset import Asset
from atlas.market.asset_type import AssetType
from atlas.market.asset_universe import AssetUniverse


class FakeAssetProvider:
    def list_assets(self):
        return [
            Asset(
                symbol="BTC-USD",
                name="Bitcoin",
                asset_type=AssetType.CRYPTO,
                market="crypto",
                currency="USD",
            ),
            Asset(
                symbol="NVDA",
                name="NVIDIA",
                asset_type=AssetType.STOCK,
                market="US",
                currency="USD",
            ),
            Asset(
                symbol="QQQ",
                name="Invesco QQQ",
                asset_type=AssetType.ETF,
                market="US",
                currency="USD",
            ),
        ]


def test_universe_can_load_assets_from_provider():

    universe = AssetUniverse(
        provider=FakeAssetProvider()
    )

    assert universe.count() == 3
    assert universe.get("BTC-USD") is not None
    assert universe.get("NVDA").asset_type == (
        AssetType.STOCK
    )


def test_explicit_assets_still_override_provider():

    assets = [
        Asset(
            symbol="AAPL",
            name="Apple",
            asset_type=AssetType.STOCK,
            market="US",
            currency="USD",
        )
    ]

    universe = AssetUniverse(
        assets=assets,
        provider=FakeAssetProvider(),
    )

    assert universe.count() == 1
    assert universe.get("AAPL") is not None
    assert universe.get("BTC-USD") is None


def test_universe_can_add_dynamic_asset():

    universe = AssetUniverse(
        assets=[]
    )

    asset = Asset(
        symbol="PLTR",
        name="Palantir Technologies Inc.",
        asset_type=AssetType.STOCK,
        market="NMS",
        currency="USD",
    )

    added = universe.add(asset)

    assert added is True
    assert universe.get("PLTR") == asset
    assert universe.count() == 1


def test_universe_does_not_duplicate_existing_asset():

    universe = AssetUniverse(
        assets=[
            Asset(
                symbol="NVDA",
                name="NVIDIA",
                asset_type=AssetType.STOCK,
                market="US",
                currency="USD",
            )
        ]
    )

    duplicate = Asset(
        symbol="NVDA",
        name="NVIDIA Corporation",
        asset_type=AssetType.STOCK,
        market="US",
        currency="USD",
    )

    added = universe.add(duplicate)

    assert added is False
    assert universe.count() == 1
    assert universe.get("NVDA").name == "NVIDIA"


def test_universe_can_add_multiple_dynamic_assets():

    universe = AssetUniverse(
        assets=[]
    )

    assets = [
        Asset(
            symbol="PLTR",
            name="Palantir Technologies Inc.",
            asset_type=AssetType.STOCK,
            market="NMS",
            currency="USD",
        ),
        Asset(
            symbol="XRP-USD",
            name="XRP",
            asset_type=AssetType.CRYPTO,
            market="crypto",
            currency="USD",
        ),
    ]

    added = universe.add_all(assets)

    assert added == 2
    assert universe.count() == 2
    assert universe.get("PLTR") is not None
    assert universe.get("XRP-USD") is not None
