from atlas.trading.crypto_intelligence_snapshot import (
    CryptoIntelligenceSnapshot,
)
from atlas.trading.crypto_market_breadth import (
    CryptoMarketBreadthAnalyzer,
)
from atlas.trading.crypto_market_context import (
    CryptoMarketContextBuilder,
)


def _asset():
    return CryptoMarketContextBuilder.asset_from_market(
        {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "current_price": 100000,
            "market_cap": 2000000000000,
            "market_cap_rank": 1,
            "total_volume": 50000000000,
            "price_change_percentage_24h": 3.0,
        }
    )


def _global():
    return CryptoMarketContextBuilder.global_context(
        {
            "data": {
                "total_market_cap": {
                    "usd": 4000000000000
                },
                "total_volume": {
                    "usd": 150000000000
                },
                "market_cap_change_percentage_24h_usd": 2.0,
                "market_cap_percentage": {
                    "btc": 58.0,
                    "eth": 12.0,
                },
            }
        }
    )


def _breadth():
    assets = [
        _asset(),
        CryptoMarketContextBuilder.asset_from_market(
            {
                "id": "ethereum",
                "symbol": "eth",
                "name": "Ethereum",
                "current_price": 4000,
                "market_cap": 480000000000,
                "market_cap_rank": 2,
                "total_volume": 25000000000,
                "price_change_percentage_24h": 2.0,
            }
        ),
    ]

    return CryptoMarketBreadthAnalyzer().analyze(
        assets
    )


def test_snapshot_builds_good_market_intelligence():
    result = CryptoIntelligenceSnapshot.build(
        symbol="BTC-USD",
        asset=_asset(),
        global_market=_global(),
        breadth=_breadth(),
        technical_signal="BUY",
        multi_timeframe_signal="BUY",
        market_alignment=0.85,
        confidence=88.0,
    )

    assert result.symbol == "BTC-USD"
    assert result.asset.symbol == "BTC"

    assert result.global_market.btc_dominance == 58.0

    assert result.technical_signal == "BUY"
    assert result.multi_timeframe_signal == "BUY"

    assert result.market_alignment == 0.85
    assert result.confidence == 88.0

    assert result.data_quality == "GOOD"


def test_snapshot_exposes_breadth_regime():
    result = CryptoIntelligenceSnapshot.build(
        symbol="BTC-USD",
        asset=_asset(),
        global_market=_global(),
        breadth=_breadth(),
    )

    assert (
        result.market_regime
        == "BROAD_BULLISH"
    )


def test_good_buy_snapshot_is_actionable():
    result = CryptoIntelligenceSnapshot.build(
        symbol="BTC-USD",
        asset=_asset(),
        global_market=_global(),
        breadth=_breadth(),
        technical_signal="BUY",
        multi_timeframe_signal="BUY",
        market_alignment=0.8,
        confidence=80.0,
    )

    assert result.is_actionable is True


def test_wait_snapshot_is_not_actionable():
    result = CryptoIntelligenceSnapshot.build(
        symbol="BTC-USD",
        asset=_asset(),
        global_market=_global(),
        breadth=_breadth(),
        technical_signal="WAIT",
        multi_timeframe_signal="WAIT",
        market_alignment=0.8,
        confidence=80.0,
    )

    assert result.is_actionable is False


def test_missing_data_blocks_actionability():
    asset = CryptoMarketContextBuilder.asset_from_market(
        {}
    )

    result = CryptoIntelligenceSnapshot.build(
        symbol="BTC-USD",
        asset=asset,
        global_market=_global(),
        breadth=_breadth(),
        technical_signal="BUY",
        multi_timeframe_signal="BUY",
        market_alignment=0.9,
        confidence=95.0,
    )

    assert result.data_quality == "MISSING"
    assert result.confidence == 0.0
    assert result.market_alignment == 0.0
    assert result.is_actionable is False


def test_partial_data_blocks_actionability():
    breadth = CryptoMarketBreadthAnalyzer().analyze(
        [
            _asset(),
            CryptoMarketContextBuilder.asset_from_market(
                {}
            ),
        ]
    )

    result = CryptoIntelligenceSnapshot.build(
        symbol="BTC-USD",
        asset=_asset(),
        global_market=_global(),
        breadth=breadth,
        technical_signal="BUY",
        multi_timeframe_signal="BUY",
        market_alignment=0.9,
        confidence=95.0,
    )

    assert result.data_quality in {
        "PARTIAL",
        "POOR",
    }

    assert result.confidence == 0.0
    assert result.is_actionable is False
