from atlas.trading.crypto_intelligence_bridge import (
    CryptoIntelligenceContextBridge,
)
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
            "price_change_percentage_24h": 3.5,
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
        CryptoMarketContextBuilder.asset_from_market(
            {
                "id": "solana",
                "symbol": "sol",
                "name": "Solana",
                "current_price": 200,
                "market_cap": 100000000000,
                "total_volume": 5000000000,
                "price_change_percentage_24h": 1.0,
            }
        ),
    ]

    return CryptoMarketBreadthAnalyzer().analyze(
        assets
    )


def _snapshot(
    technical_signal="BUY",
    mtf_signal="BUY",
    confidence=90.0,
):
    return CryptoIntelligenceSnapshot.build(
        symbol="BTC-USD",
        asset=_asset(),
        global_market=_global(),
        breadth=_breadth(),
        technical_signal=technical_signal,
        multi_timeframe_signal=mtf_signal,
        market_alignment=0.85,
        confidence=confidence,
    )


def test_bridge_exposes_snapshot_context():
    snapshot = _snapshot()

    result = (
        CryptoIntelligenceContextBridge.build(
            snapshot
        )
    )

    assert result.symbol == "BTC-USD"

    assert result.asset_change_24h == 3.5
    assert result.asset_market_cap_rank == 1

    assert result.technical_signal == "BUY"
    assert result.multi_timeframe_signal == "BUY"

    assert result.market_regime == "BROAD_BULLISH"
    assert result.advance_ratio == 1.0
    assert result.decline_ratio == 0.0

    assert result.btc_dominance == 58.0
    assert result.eth_dominance == 12.0
    assert result.market_cap_change_24h == 2.0

    assert result.market_alignment == 0.85
    assert result.confidence == 90.0

    assert result.data_quality == "GOOD"
    assert result.actionable is True


def test_bridge_preserves_wait_signal():
    snapshot = _snapshot(
        technical_signal="WAIT",
        mtf_signal="WAIT",
        confidence=45.0,
    )

    result = (
        CryptoIntelligenceContextBridge.build(
            snapshot
        )
    )

    assert result.technical_signal == "WAIT"
    assert result.multi_timeframe_signal == "WAIT"
    assert result.confidence == 45.0
    assert result.actionable is False


def test_bridge_preserves_sell_signal():
    snapshot = _snapshot(
        technical_signal="SELL",
        mtf_signal="SELL",
        confidence=85.0,
    )

    result = (
        CryptoIntelligenceContextBridge.build(
            snapshot
        )
    )

    assert result.technical_signal == "SELL"
    assert result.multi_timeframe_signal == "SELL"
    assert result.actionable is True


def test_bridge_does_not_change_snapshot():
    snapshot = _snapshot()

    before = (
        snapshot.symbol,
        snapshot.technical_signal,
        snapshot.multi_timeframe_signal,
        snapshot.confidence,
        snapshot.data_quality,
    )

    CryptoIntelligenceContextBridge.build(
        snapshot
    )

    after = (
        snapshot.symbol,
        snapshot.technical_signal,
        snapshot.multi_timeframe_signal,
        snapshot.confidence,
        snapshot.data_quality,
    )

    assert after == before


def test_bridge_exposes_optional_derivatives_flow_without_changing_signal():
    from atlas.trading.historical_derivatives_data import (
        DerivativesFlowObservation,
    )

    flow = DerivativesFlowObservation(
        timestamp=1_791_279_000.0,
        spot_taker_buy_ratio=0.80,
        futures_taker_buy_ratio=0.40,
        open_interest_change=0.02,
    )

    snapshot = CryptoIntelligenceSnapshot.build(
        symbol="BTC-USD",
        asset=_asset(),
        global_market=_global(),
        breadth=_breadth(),
        technical_signal="WAIT",
        multi_timeframe_signal="WAIT",
        market_alignment=0.0,
        confidence=0.0,
        derivatives_flow=flow,
    )

    result = CryptoIntelligenceContextBridge.build(snapshot)

    assert result.derivatives_flow is flow
    assert result.technical_signal == "WAIT"
    assert result.multi_timeframe_signal == "WAIT"
    assert result.confidence == 0.0
    assert result.actionable is False
