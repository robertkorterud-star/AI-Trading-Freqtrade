from atlas.services.crypto_market_service import (
    CryptoMarketService,
)


class FakeCoinGecko:

    def get_coin(self, coin_id):
        return {
            "id": coin_id,
            "symbol": "btc",
            "name": "Bitcoin",
            "market_cap_rank": 1,
            "market_data": {
                "current_price": {
                    "usd": 100000,
                },
                "market_cap": {
                    "usd": 2000000000000,
                },
                "total_volume": {
                    "usd": 50000000000,
                },
                "price_change_percentage_24h": 2.0,
            },
        }

    def get_markets(
        self,
        vs_currency,
        page,
        per_page,
    ):
        return [
            {
                "id": "bitcoin",
                "symbol": "btc",
                "name": "Bitcoin",
                "current_price": 100000,
                "market_cap": 2000000000000,
                "market_cap_rank": 1,
                "total_volume": 50000000000,
                "price_change_percentage_24h": 2.0,
            },
            {
                "id": "ethereum",
                "symbol": "eth",
                "name": "Ethereum",
                "current_price": 4000,
                "market_cap": 480000000000,
                "market_cap_rank": 2,
                "total_volume": 25000000000,
                "price_change_percentage_24h": 3.0,
            },
        ]

    def get_global_market(self):
        return {
            "data": {
                "total_market_cap": {
                    "usd": 4000000000000,
                },
                "total_volume": {
                    "usd": 150000000000,
                },
                "market_cap_change_percentage_24h_usd": 1.5,
                "market_cap_percentage": {
                    "btc": 58.0,
                    "eth": 12.0,
                },
            }
        }


def test_get_asset_returns_normalized_context():
    service = CryptoMarketService(
        coingecko=FakeCoinGecko()
    )

    result = service.get_asset(
        "bitcoin"
    )

    assert result.coin_id == "bitcoin"
    assert result.symbol == "BTC"
    assert result.price == 100000.0
    assert result.market_cap_rank == 1
    assert result.data_quality == "GOOD"


def test_get_markets_returns_normalized_assets():
    service = CryptoMarketService(
        coingecko=FakeCoinGecko()
    )

    result = service.get_markets(
        vs_currency="usd",
        page=1,
        per_page=100,
    )

    assert len(result) == 2

    assert result[0].symbol == "BTC"
    assert result[0].price == 100000.0

    assert result[1].symbol == "ETH"
    assert result[1].price == 4000.0


def test_get_global_context_returns_normalized_context():
    service = CryptoMarketService(
        coingecko=FakeCoinGecko()
    )

    result = service.get_global_context()

    assert result.total_market_cap == 4000000000000.0
    assert result.total_volume_24h == 150000000000.0
    assert result.btc_dominance == 58.0
    assert result.eth_dominance == 12.0
    assert result.data_quality == "GOOD"


def test_get_market_asset_normalizes_direct_response():
    service = CryptoMarketService(
        coingecko=FakeCoinGecko()
    )

    result = service.get_market_asset(
        {
            "id": "solana",
            "symbol": "sol",
            "name": "Solana",
            "current_price": 200,
            "market_cap": 100000000000,
            "market_cap_rank": 5,
            "total_volume": 5000000000,
        }
    )

    assert result.coin_id == "solana"
    assert result.symbol == "SOL"
    assert result.price == 200.0
    assert result.data_quality == "GOOD"
