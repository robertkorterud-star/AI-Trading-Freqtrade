from atlas.market.asset import Asset
from atlas.market.asset_type import AssetType
from atlas.market.asset_universe import AssetUniverse


def test_asset_contains_market_identity():

    asset = Asset(
        symbol="BTC-USD",
        name="Bitcoin",
        asset_type=AssetType.CRYPTO,
        market="crypto",
        currency="USD",
    )

    assert asset.symbol == "BTC-USD"
    assert asset.name == "Bitcoin"
    assert asset.asset_type == AssetType.CRYPTO
    assert asset.market == "crypto"
    assert asset.currency == "USD"
    assert asset.active is True


def test_default_universe_contains_multiple_asset_classes():

    universe = AssetUniverse()

    assert universe.count() == 7

    assert universe.get("BTC-USD") is not None
    assert universe.get("NVDA") is not None
    assert universe.get("QQQ") is not None

    assert len(
        universe.by_type(AssetType.CRYPTO)
    ) == 3

    assert len(
        universe.by_type(AssetType.STOCK)
    ) == 3

    assert len(
        universe.by_type(AssetType.ETF)
    ) == 1


def test_universe_returns_symbols():

    universe = AssetUniverse()

    symbols = universe.symbols()

    assert "BTC-USD" in symbols
    assert "NVDA" in symbols
    assert "QQQ" in symbols


def test_universe_can_be_configured():

    universe = AssetUniverse(
        [
            Asset(
                symbol="SOL-USD",
                name="Solana",
                asset_type=AssetType.CRYPTO,
                market="crypto",
                currency="USD",
            ),
            Asset(
                symbol="TSLA",
                name="Tesla",
                asset_type=AssetType.STOCK,
                market="US",
                currency="USD",
            ),
        ]
    )

    assert universe.count() == 2
    assert universe.get("SOL-USD").asset_type == (
        AssetType.CRYPTO
    )
    assert universe.get("TSLA").asset_type == (
        AssetType.STOCK
    )


def test_inactive_assets_are_excluded():

    universe = AssetUniverse(
        [
            Asset(
                symbol="BTC-USD",
                name="Bitcoin",
                asset_type=AssetType.CRYPTO,
                market="crypto",
                currency="USD",
            ),
            Asset(
                symbol="DELISTED",
                name="Inactive Asset",
                asset_type=AssetType.STOCK,
                market="US",
                currency="USD",
                active=False,
            ),
        ]
    )

    assert universe.count() == 1
    assert universe.get("DELISTED") is None
