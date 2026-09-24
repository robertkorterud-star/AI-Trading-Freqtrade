from atlas.market.asset import Asset
from atlas.market.asset_discovery import DiscoveryScore
from atlas.market.asset_universe import AssetUniverse
from atlas.market.candidates.market_discovery import MarketDiscoverySource


class FakeDiscovery:
    def __init__(self, results):
        self.results = results
        self.calls = 0
        self.received_universe = None
        self.received_limit = None

    def discover(self, universe, limit=None):
        self.calls += 1
        self.received_universe = universe
        self.received_limit = limit
        return list(self.results)


def test_market_discovery_source_uses_existing_discovery_service():
    asset = Asset(symbol="AAPL", name="Apple", asset_type="stock", market="NASDAQ", currency="USD")
    universe = AssetUniverse(assets=[asset])

    discovery = FakeDiscovery(
        [
            DiscoveryScore(
                asset=asset,
                score=82.5,
            )
        ]
    )

    source = MarketDiscoverySource(
        discovery=discovery,
        universe=universe,
        limit=5,
    )

    result = source.discover()

    assert discovery.calls == 1
    assert discovery.received_universe is universe
    assert discovery.received_limit == 5

    assert len(result) == 1
    assert result[0].symbol == "AAPL"
    assert result[0].source == "market_discovery"
    assert result[0].score == 82.5


def test_market_discovery_source_applies_minimum_score():
    assets = [
        Asset(symbol="AAPL", name="Apple", asset_type="stock", market="NASDAQ", currency="USD"),
        Asset(symbol="NVDA", name="NVIDIA", asset_type="stock", market="NASDAQ", currency="USD"),
    ]
    universe = AssetUniverse(assets=assets)

    discovery = FakeDiscovery(
        [
            DiscoveryScore(asset=assets[0], score=75),
            DiscoveryScore(asset=assets[1], score=40),
        ]
    )

    source = MarketDiscoverySource(
        discovery=discovery,
        universe=universe,
        minimum_score=50,
    )

    result = source.discover()

    assert [candidate.symbol for candidate in result] == ["AAPL"]


def test_market_discovery_source_preserves_discovery_order():
    assets = [
        Asset(symbol="AAPL", name="Apple", asset_type="stock", market="NASDAQ", currency="USD"),
        Asset(symbol="NVDA", name="NVIDIA", asset_type="stock", market="NASDAQ", currency="USD"),
    ]
    universe = AssetUniverse(assets=assets)

    discovery = FakeDiscovery(
        [
            DiscoveryScore(asset=assets[1], score=90),
            DiscoveryScore(asset=assets[0], score=80),
        ]
    )

    source = MarketDiscoverySource(
        discovery=discovery,
        universe=universe,
    )

    result = source.discover()

    assert [candidate.symbol for candidate in result] == [
        "NVDA",
        "AAPL",
    ]


def test_market_discovery_source_can_return_no_candidates():
    universe = AssetUniverse(assets=[])

    discovery = FakeDiscovery([])

    source = MarketDiscoverySource(
        discovery=discovery,
        universe=universe,
    )

    assert source.discover() == []

def test_market_discovery_source_carries_discovery_evidence():
    asset = Asset(
        symbol="AAPL",
        name="Apple",
        asset_type="stock",
        market="NASDAQ",
        currency="USD",
    )
    universe = AssetUniverse(assets=[asset])

    from atlas.market.asset_discovery import DiscoveryInput

    discovery = FakeDiscovery(
        [
            DiscoveryScore(
                asset=asset,
                score=82.5,
                discovery_input=DiscoveryInput(
                    volume_score=90,
                    momentum_score=80,
                    volatility_score=70,
                    news_score=0,
                    liquidity_score=95,
                ),
            )
        ]
    )

    candidate = MarketDiscoverySource(
        discovery=discovery,
        universe=universe,
    ).discover()[0]

    assert candidate.metadata == {
        "volume_score": 90,
        "momentum_score": 80,
        "volatility_score": 70,
        "news_score": 0,
        "liquidity_score": 95,
    }


def test_market_discovery_source_forwards_and_carries_horizon_context():
    from atlas.market.trading_horizon import TradingHorizon

    asset = Asset(
        symbol="NVDA",
        name="NVIDIA",
        asset_type="stock",
        market="NASDAQ",
        currency="USD",
    )
    universe = AssetUniverse(assets=[asset])

    class HorizonDiscovery:
        def __init__(self):
            self.received_horizon = None

        def discover(self, universe, limit=None, horizon=None):
            self.received_horizon = horizon
            return [
                DiscoveryScore(
                    asset=asset,
                    score=88.0,
                    horizon=horizon,
                )
            ]

    discovery = HorizonDiscovery()
    source = MarketDiscoverySource(
        discovery=discovery,
        universe=universe,
        horizon=TradingHorizon.DAY_TRADE,
    )

    candidate = source.discover()[0]

    assert discovery.received_horizon == TradingHorizon.DAY_TRADE
    assert candidate.metadata["horizon"] == TradingHorizon.DAY_TRADE.value
