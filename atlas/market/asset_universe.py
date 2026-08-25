from atlas.market.asset import Asset
from atlas.market.asset_type import AssetType


class AssetUniverse:
    """Collection of assets available to ATLAS."""

    DEFAULT_ASSETS = (
        Asset(
            symbol="BTC-USD",
            name="Bitcoin",
            asset_type=AssetType.CRYPTO,
            market="crypto",
            currency="USD",
        ),
        Asset(
            symbol="ETH-USD",
            name="Ethereum",
            asset_type=AssetType.CRYPTO,
            market="crypto",
            currency="USD",
        ),
        Asset(
            symbol="XRP-USD",
            name="XRP",
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
            symbol="AAPL",
            name="Apple",
            asset_type=AssetType.STOCK,
            market="US",
            currency="USD",
        ),
        Asset(
            symbol="MSFT",
            name="Microsoft",
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
    )

    def __init__(
        self,
        assets=None,
        provider=None,
    ):
        if assets is not None:
            source = tuple(assets)

        elif provider is not None:
            source = tuple(
                provider.list_assets()
            )

        else:
            source = self.DEFAULT_ASSETS

        self._assets = {
            asset.symbol: asset
            for asset in source
            if asset.active
        }

    def add(self, asset: Asset) -> bool:
        """Add an active asset if it is not already known."""

        if not asset.active:
            return False

        if asset.symbol in self._assets:
            return False

        self._assets[asset.symbol] = asset

        return True

    def add_all(self, assets) -> int:
        """Add active assets and return the number added."""

        added = 0

        for asset in assets:
            if self.add(asset):
                added += 1

        return added

    def all(self):
        """Return all active assets."""

        return list(self._assets.values())

    def get(self, symbol: str):
        """Return an asset by symbol."""

        return self._assets.get(symbol)

    def by_type(self, asset_type: AssetType):
        """Return active assets for one asset class."""

        return [
            asset
            for asset in self._assets.values()
            if asset.asset_type == asset_type
        ]

    def symbols(self):
        """Return active asset symbols."""

        return list(self._assets)

    def count(self):
        """Return number of active assets."""

        return len(self._assets)
