from atlas.market.asset import Asset
from atlas.market.asset_type import AssetType
from atlas.market.asset_universe import AssetUniverse
from atlas.market.asset_discovery import (
    AssetDiscoveryService,
    DiscoveryInput,
)


def test_discovery_score_combines_market_signals():

    asset = Asset(
        symbol="BTC-USD",
        name="Bitcoin",
        asset_type=AssetType.CRYPTO,
        market="crypto",
        currency="USD",
    )

    discovery = AssetDiscoveryService()

    score = discovery.score(
        asset,
        DiscoveryInput(
            volume_score=90.0,
            momentum_score=80.0,
            volatility_score=70.0,
            news_score=60.0,
            liquidity_score=100.0,
        ),
    )

    assert score.symbol == "BTC-USD"
    assert score.score == 80.0


def test_discovery_ranks_candidates():

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
        ]
    )

    discovery = AssetDiscoveryService()

    results = discovery.rank(
        universe,
        {
            "BTC-USD": DiscoveryInput(
                volume_score=90.0,
                momentum_score=90.0,
                volatility_score=80.0,
                news_score=70.0,
                liquidity_score=100.0,
            ),
            "NVDA": DiscoveryInput(
                volume_score=70.0,
                momentum_score=80.0,
                volatility_score=60.0,
                news_score=90.0,
                liquidity_score=90.0,
            ),
            "AAPL": DiscoveryInput(
                volume_score=50.0,
                momentum_score=50.0,
                volatility_score=40.0,
                news_score=50.0,
                liquidity_score=80.0,
            ),
        },
    )

    assert [result.symbol for result in results] == [
        "BTC-USD",
        "NVDA",
        "AAPL",
    ]


def test_discovery_can_limit_candidates():

    universe = AssetUniverse()

    discovery = AssetDiscoveryService()

    market_data = {
        asset.symbol: DiscoveryInput(
            volume_score=80.0,
            momentum_score=80.0,
            volatility_score=80.0,
            news_score=80.0,
            liquidity_score=80.0,
        )
        for asset in universe.all()
    }

    results = discovery.rank(
        universe,
        market_data,
        limit=3,
    )

    assert len(results) == 3


def test_discovery_defaults_missing_assets_to_zero():

    universe = AssetUniverse()

    discovery = AssetDiscoveryService()

    results = discovery.rank(
        universe,
        {},
    )

    assert len(results) == universe.count()

    assert all(
        result.score == 0.0
        for result in results
    )


def test_discovery_skips_assets_with_unavailable_market_data(
    monkeypatch,
):
    class FakeMarketData:

        def get(self, symbol):
            if symbol == "ETH-USD":
                raise ValueError(
                    "Insufficient market history"
                )

            return type(
                "MarketData",
                (),
                {
                    "price": 120.0,
                    "ma50": 100.0,
                    "change_percent": 2.0,
                    "volume_ratio": 2.0,
                },
            )()

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
                symbol="ETH-USD",
                name="Ethereum",
                asset_type=AssetType.CRYPTO,
                market="crypto",
                currency="USD",
            ),
        ]
    )

    discovery = AssetDiscoveryService(
        market_data=FakeMarketData()
    )

    results = discovery.discover(
        universe
    )

    assert [
        result.symbol
        for result in results
    ] == ["BTC-USD"]


def test_discovery_returns_empty_when_all_assets_are_unavailable():

    class FakeMarketData:

        def get(self, symbol):
            raise ValueError(
                "Insufficient market history"
            )

    universe = AssetUniverse(
        [
            Asset(
                symbol="BTC-USD",
                name="Bitcoin",
                asset_type=AssetType.CRYPTO,
                market="crypto",
                currency="USD",
            ),
        ]
    )

    discovery = AssetDiscoveryService(
        market_data=FakeMarketData()
    )

    assert discovery.discover(universe) == []
