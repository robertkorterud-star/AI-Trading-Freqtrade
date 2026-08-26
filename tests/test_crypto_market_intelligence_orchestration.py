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
        return {
            "signal": "BUY",
            "confidence": 82.0,
        }


class FakeMultiTimeframeService:

    def analyze(self, symbol):
        return type(
            "FakeMTFResult",
            (),
            {
                "overall_signal": "BUY",
                "confidence": 90.0,
                "alignment": 92.0,
                "data_quality": "GOOD",
            },
        )()


def test_orchestration_uses_existing_analysis_services():

    technical = FakeTechnicalAnalyzer()
    mtf = FakeMultiTimeframeService()

    service = CryptoMarketIntelligenceService(
        crypto_market_service=FakeCryptoMarketService(),
        breadth_analyzer=CryptoMarketBreadthAnalyzer(),
        technical_analyzer=technical,
        multi_timeframe_service=mtf,
    )

    result = service.analyze_with_market_data(
        coin_id="bitcoin",
        symbol="BTC-USD",
        candles=[
            {
                "open": 100,
                "high": 105,
                "low": 99,
                "close": 104,
                "volume": 1000,
            }
        ],
    )

    assert result.technical_signal == "BUY"
    assert result.multi_timeframe_signal == "BUY"

    assert result.confidence > 0
    assert result.market_alignment > 0

    assert result.data_quality == "GOOD"


def test_orchestration_does_not_replace_mtf_service():

    mtf = FakeMultiTimeframeService()

    service = CryptoMarketIntelligenceService(
        crypto_market_service=FakeCryptoMarketService(),
        breadth_analyzer=CryptoMarketBreadthAnalyzer(),
        technical_analyzer=FakeTechnicalAnalyzer(),
        multi_timeframe_service=mtf,
    )

    result = service.analyze_with_market_data(
        coin_id="bitcoin",
        symbol="BTC-USD",
        candles=[],
    )

    assert result.multi_timeframe_signal == "BUY"
