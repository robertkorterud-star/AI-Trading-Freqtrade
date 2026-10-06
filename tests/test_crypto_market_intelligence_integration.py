from atlas.services.crypto_market_intelligence_service import (
    CryptoMarketIntelligenceService,
)
from atlas.trading.crypto_market_breadth import (
    CryptoMarketBreadthAnalyzer,
)


class FakeCryptoMarketService:

    def get_asset(self, coin_id):
        from atlas.trading.crypto_market_context import (
            CryptoMarketContextBuilder,
        )

        return CryptoMarketContextBuilder.asset_from_market(
            {
                "id": coin_id,
                "symbol": "btc",
                "name": "Bitcoin",
                "current_price": 100000,
                "market_cap": 2000000000000,
                "market_cap_rank": 1,
                "total_volume": 50000000000,
                "price_change_percentage_24h": 4.0,
            }
        )

    def get_global_context(self):
        from atlas.trading.crypto_market_context import (
            CryptoMarketContextBuilder,
        )

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

    def get_markets(self):
        from atlas.trading.crypto_market_context import (
            CryptoMarketContextBuilder,
        )

        builder = CryptoMarketContextBuilder

        return [
            builder.asset_from_market(
                {
                    "id": "bitcoin",
                    "symbol": "btc",
                    "name": "Bitcoin",
                    "current_price": 100000,
                    "market_cap": 2000000000000,
                    "total_volume": 50000000000,
                    "price_change_percentage_24h": 4.0,
                }
            ),
            builder.asset_from_market(
                {
                    "id": "ethereum",
                    "symbol": "eth",
                    "name": "Ethereum",
                    "current_price": 4000,
                    "market_cap": 480000000000,
                    "total_volume": 25000000000,
                    "price_change_percentage_24h": 3.0,
                }
            ),
        ]


class FakeTechnicalAnalyzer:

    def analyze(self, symbol, candles):
        return "BUY"


class FakeMultiTimeframeAnalyzer:

    def analyze(self, symbol, timeframe_data):
        return "BUY"


def test_crypto_intelligence_can_accept_analysis_context():
    service = CryptoMarketIntelligenceService(
        crypto_market_service=FakeCryptoMarketService(),
        breadth_analyzer=CryptoMarketBreadthAnalyzer(),
    )

    result = service.analyze(
        coin_id="bitcoin",
        symbol="BTC-USD",
        technical_signal="BUY",
        multi_timeframe_signal="BUY",
        market_alignment=0.9,
        confidence=90.0,
    )

    assert result.technical_signal == "BUY"
    assert result.multi_timeframe_signal == "BUY"
    assert result.confidence == 90.0
    assert result.market_alignment == 0.9
    assert result.data_quality == "GOOD"


def test_crypto_intelligence_does_not_create_signal_from_market_context():
    service = CryptoMarketIntelligenceService(
        crypto_market_service=FakeCryptoMarketService(),
        breadth_analyzer=CryptoMarketBreadthAnalyzer(),
    )

    result = service.analyze(
        coin_id="bitcoin",
        symbol="BTC-USD",
        technical_signal="WAIT",
        multi_timeframe_signal="WAIT",
        market_alignment=0.0,
        confidence=0.0,
    )

    assert result.technical_signal == "WAIT"
    assert result.multi_timeframe_signal == "WAIT"
    assert result.confidence == 0.0
    assert result.is_actionable is False


def test_crypto_intelligence_can_carry_derivatives_flow_without_creating_signal():
    from atlas.trading.historical_derivatives_data import (
        DerivativesFlowObservation,
    )

    flow = DerivativesFlowObservation(
        timestamp=1_791_279_000.0,
        spot_taker_buy_ratio=0.80,
        futures_taker_buy_ratio=0.40,
        open_interest_change=0.02,
    )

    service = CryptoMarketIntelligenceService(
        crypto_market_service=FakeCryptoMarketService(),
        breadth_analyzer=CryptoMarketBreadthAnalyzer(),
    )

    result = service.analyze(
        coin_id="bitcoin",
        symbol="BTC-USD",
        technical_signal="WAIT",
        multi_timeframe_signal="WAIT",
        market_alignment=0.0,
        confidence=0.0,
        derivatives_flow=flow,
    )

    assert result.derivatives_flow is flow
    assert result.technical_signal == "WAIT"
    assert result.multi_timeframe_signal == "WAIT"
    assert result.market_alignment == 0.0
    assert result.confidence == 0.0
    assert result.is_actionable is False
