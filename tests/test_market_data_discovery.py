from types import SimpleNamespace

from atlas.market.asset import Asset
from atlas.market.asset_discovery import (
    AssetDiscoveryService,
)
from atlas.market.asset_type import AssetType


class FakeMarketDataProvider:
    def __init__(self, data):
        self.data = data

    def get(self, symbol):
        return self.data[symbol]


def test_market_data_provider_maps_market_data_to_discovery_input():

    asset = Asset(
        symbol="NVDA",
        name="NVIDIA",
        asset_type=AssetType.STOCK,
        market="US",
        currency="USD",
    )

    market_data = SimpleNamespace(
        price=120.0,
        previous_close=110.0,
        change_percent=9.09,
        ma20=112.0,
        ma50=105.0,
        volume=2_000_000.0,
        average_volume=1_000_000.0,
        volume_ratio=2.0,
    )

    provider = FakeMarketDataProvider(
        {"NVDA": market_data}
    )

    discovery = AssetDiscoveryService(
        market_data=provider,
    )

    result = discovery.market_input(asset)

    assert result.volume_score == 100.0
    assert result.momentum_score == 100.0
    assert result.volatility_score == 90.9
    assert result.news_score == 0.0
    assert result.liquidity_score == 100.0


def test_market_data_discovery_ranks_real_assets():

    assets = [
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
    ]

    market_data = {
        "BTC-USD": SimpleNamespace(
            price=100.0,
            previous_close=99.0,
            change_percent=1.01,
            ma20=99.0,
            ma50=98.0,
            volume=1_200_000.0,
            average_volume=1_000_000.0,
            volume_ratio=1.2,
        ),
        "NVDA": SimpleNamespace(
            price=120.0,
            previous_close=110.0,
            change_percent=9.09,
            ma20=112.0,
            ma50=105.0,
            volume=2_000_000.0,
            average_volume=1_000_000.0,
            volume_ratio=2.0,
        ),
    }

    universe = SimpleNamespace(
        all=lambda: assets,
    )

    provider = FakeMarketDataProvider(
        market_data
    )

    discovery = AssetDiscoveryService(
        market_data=provider,
    )

    results = discovery.discover(
        universe,
        limit=2,
    )

    assert [result.symbol for result in results] == [
        "NVDA",
        "BTC-USD",
    ]

def test_discovery_liquidity_is_not_duplicated_from_relative_volume():
    """High relative volume alone must not imply perfect liquidity."""

    asset = Asset(
        symbol="TEST",
        name="Test Asset",
        asset_type=AssetType.STOCK,
        market="US",
        currency="USD",
    )

    market_data = SimpleNamespace(
        price=100.0,
        previous_close=99.0,
        change_percent=1.0,
        ma20=99.0,
        ma50=98.0,
        volume=5_000.0,
        average_volume=1_000.0,
        volume_ratio=5.0,
    )

    discovery = AssetDiscoveryService(
        market_data=FakeMarketDataProvider(
            {"TEST": market_data}
        )
    )

    result = discovery.market_input(asset)

    assert result.volume_score == 100.0
    assert result.liquidity_score < result.volume_score
