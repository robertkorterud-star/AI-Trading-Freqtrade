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


def test_discovery_uses_batch_market_data_when_available():
    class FakeMarketData:
        def __init__(self):
            self.batch_calls = 0
            self.get_calls = 0

        def get_many(self, symbols):
            self.batch_calls += 1
            return {
                symbol: type(
                    "MarketData",
                    (),
                    {
                        "price": 120.0,
                        "ma50": 100.0,
                        "change_percent": 2.0,
                        "volume_ratio": 2.0,
                    },
                )()
                for symbol in symbols
            }

        def get(self, symbol):
            self.get_calls += 1
            raise AssertionError("batch market data should be used")

    market_data = FakeMarketData()
    discovery = AssetDiscoveryService(market_data=market_data)
    universe = AssetUniverse()

    results = discovery.discover(universe)

    assert len(results) == universe.count()
    assert market_data.batch_calls == 1
    assert market_data.get_calls == 0

def test_discovery_preserves_normalized_input_as_evidence():
    asset = Asset(
        symbol="AAPL",
        name="Apple",
        asset_type=AssetType.STOCK,
        market="US",
        currency="USD",
    )

    class FakeMarketData:
        def get_many(self, symbols):
            return {
                "AAPL": type(
                    "MarketData",
                    (),
                    {
                        "price": 120.0,
                        "ma50": 100.0,
                        "change_percent": 2.0,
                        "volume_ratio": 2.0,
                    },
                )()
            }

    result = AssetDiscoveryService(
        market_data=FakeMarketData()
    ).discover(
        AssetUniverse(assets=[asset]),
        timestamp=0,
    )[0]

    assert result.discovery_input is not None
    assert result.discovery_input.momentum_score == 100.0
    assert result.discovery_input.volatility_score == 20.0
    assert result.discovery_input.volume_score == 100.0
    assert result.discovery_input.liquidity_score == 100.0


def test_discovery_score_preserves_horizon_as_ranking_context():
    from atlas.market.trading_horizon import TradingHorizon

    asset = Asset(
        symbol="NVDA",
        name="NVIDIA",
        asset_type=AssetType.STOCK,
        market="US",
        currency="USD",
    )

    result = AssetDiscoveryService().score(
        asset,
        DiscoveryInput(
            volume_score=80.0,
            momentum_score=90.0,
            volatility_score=70.0,
            news_score=0.0,
            liquidity_score=85.0,
        ),
        horizon=TradingHorizon.DAY_TRADE,
    )

    assert result.horizon == TradingHorizon.DAY_TRADE
    assert result.score == 65.0


def test_discovery_rank_preserves_horizon_without_changing_score_formula():
    from atlas.market.trading_horizon import TradingHorizon

    asset = Asset(
        symbol="BTC-USD",
        name="Bitcoin",
        asset_type=AssetType.CRYPTO,
        market="crypto",
        currency="USD",
    )
    universe = AssetUniverse([asset])
    signals = DiscoveryInput(
        volume_score=90.0,
        momentum_score=80.0,
        volatility_score=70.0,
        news_score=60.0,
        liquidity_score=100.0,
    )

    result = AssetDiscoveryService().rank(
        universe,
        {"BTC-USD": signals},
        horizon=TradingHorizon.SWING,
    )[0]

    assert result.horizon == TradingHorizon.SWING
    assert result.score == 80.0


def test_discovery_preserves_horizon_through_market_context_enrichment():
    from atlas.market.trading_horizon import TradingHorizon

    asset = Asset(
        symbol="NVDA",
        name="NVIDIA",
        asset_type=AssetType.STOCK,
        market="US",
        currency="USD",
    )

    class FakeMarketData:
        def get_many(self, symbols):
            return {
                "NVDA": type(
                    "MarketData",
                    (),
                    {
                        "price": 120.0,
                        "ma50": 100.0,
                        "change_percent": 2.0,
                        "volume_ratio": 2.0,
                    },
                )()
            }

    result = AssetDiscoveryService(
        market_data=FakeMarketData()
    ).discover(
        AssetUniverse(assets=[asset]),
        timestamp=0,
        horizon=TradingHorizon.DAY_TRADE,
    )[0]

    assert result.horizon == TradingHorizon.DAY_TRADE
    assert result.market_context is not None
    assert result.discovery_input is not None
