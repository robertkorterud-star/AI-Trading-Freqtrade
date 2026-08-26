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

        return (
            CryptoMarketContextBuilder
            .asset_from_market(
                {
                    "id": coin_id,
                    "symbol": "btc",
                    "name": "Bitcoin",
                    "current_price": 100000,
                    "market_cap": 2000000000000,
                    "market_cap_rank": 1,
                    "total_volume": 50000000000,
                    "price_change_percentage_24h": 3.0,
                }
            )
        )

    def get_global_context(self):
        from atlas.trading.crypto_market_context import (
            CryptoMarketContextBuilder,
        )

        return (
            CryptoMarketContextBuilder
            .global_context(
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
            builder.asset_from_market(
                {
                    "id": "solana",
                    "symbol": "sol",
                    "name": "Solana",
                    "current_price": 200,
                    "market_cap": 100000000000,
                    "total_volume": 5000000000,
                    "price_change_percentage_24h": 2.0,
                }
            ),
        ]


def test_service_builds_crypto_intelligence():

    service = (
        CryptoMarketIntelligenceService(
            crypto_market_service=(
                FakeCryptoMarketService()
            ),
            breadth_analyzer=(
                CryptoMarketBreadthAnalyzer()
            ),
        )
    )

    result = service.analyze(
        coin_id="bitcoin",
        symbol="BTC-USD",
        technical_signal="BUY",
        multi_timeframe_signal="BUY",
        market_alignment=0.9,
        confidence=90.0,
    )

    assert result.symbol == "BTC-USD"
    assert result.asset.symbol == "BTC"

    assert (
        result.global_market.btc_dominance
        == 58.0
    )

    assert result.breadth.total_assets == 3
    assert result.breadth.advancing_assets == 3

    assert result.technical_signal == "BUY"
    assert result.multi_timeframe_signal == "BUY"

    assert result.data_quality == "GOOD"
    assert result.confidence == 90.0


def test_service_blocks_bad_market_context():

    service = (
        CryptoMarketIntelligenceService(
            crypto_market_service=(
                FakeCryptoMarketService()
            ),
            breadth_analyzer=(
                CryptoMarketBreadthAnalyzer()
            ),
        )
    )

    result = service.analyze(
        coin_id="bitcoin",
        symbol="BTC-USD",
        technical_signal="BUY",
        multi_timeframe_signal="BUY",
        market_alignment=0.9,
        confidence=90.0,
    )

    assert result.is_actionable is True
