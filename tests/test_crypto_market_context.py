from atlas.trading.crypto_market_context import (
    CryptoMarketContextBuilder,
)


def test_asset_from_market_builds_context():
    data = {
        "id": "bitcoin",
        "symbol": "btc",
        "name": "Bitcoin",
        "current_price": 100000,
        "market_cap": 2000000000000,
        "market_cap_rank": 1,
        "total_volume": 50000000000,
        "price_change_percentage_24h": 2.5,
        "price_change_percentage_7d_in_currency": 5.0,
        "price_change_percentage_30d_in_currency": 12.0,
        "circulating_supply": 19000000,
        "total_supply": 21000000,
    }

    result = CryptoMarketContextBuilder.asset_from_market(
        data
    )

    assert result.coin_id == "bitcoin"
    assert result.symbol == "BTC"
    assert result.name == "Bitcoin"

    assert result.price == 100000.0
    assert result.market_cap == 2000000000000.0
    assert result.market_cap_rank == 1
    assert result.volume_24h == 50000000000.0

    assert result.change_24h == 2.5
    assert result.change_7d == 5.0
    assert result.change_30d == 12.0

    assert result.data_quality == "GOOD"


def test_asset_from_coin_normalizes_nested_data():
    data = {
        "id": "ethereum",
        "symbol": "eth",
        "name": "Ethereum",
        "market_cap_rank": 2,
        "market_data": {
            "current_price": {
                "usd": 4000
            },
            "market_cap": {
                "usd": 480000000000
            },
            "total_volume": {
                "usd": 25000000000
            },
            "price_change_percentage_24h": 3.0,
            "price_change_percentage_7d_in_currency": {
                "usd": 7.0
            },
            "price_change_percentage_30d_in_currency": {
                "usd": 15.0
            },
            "circulating_supply": 120000000,
            "total_supply": 120000000,
        },
    }

    result = CryptoMarketContextBuilder.asset_from_coin(
        data
    )

    assert result.coin_id == "ethereum"
    assert result.symbol == "ETH"
    assert result.price == 4000.0
    assert result.market_cap_rank == 2
    assert result.change_7d == 7.0
    assert result.change_30d == 15.0
    assert result.data_quality == "GOOD"


def test_global_context_builds_market_context():
    data = {
        "data": {
            "total_market_cap": {
                "usd": 4000000000000
            },
            "total_volume": {
                "usd": 150000000000
            },
            "market_cap_change_percentage_24h_usd": 1.5,
            "market_cap_percentage": {
                "btc": 58.0,
                "eth": 12.0,
            },
        }
    }

    result = CryptoMarketContextBuilder.global_context(
        data
    )

    assert result.total_market_cap == 4000000000000.0
    assert result.total_volume_24h == 150000000000.0
    assert result.market_cap_change_24h == 1.5

    assert result.btc_dominance == 58.0
    assert result.eth_dominance == 12.0

    assert result.data_quality == "GOOD"


def test_missing_asset_data_is_safe():
    result = CryptoMarketContextBuilder.asset_from_market(
        {}
    )

    assert result.coin_id == ""
    assert result.symbol == ""
    assert result.price is None
    assert result.data_quality == "MISSING"


def test_missing_global_data_is_safe():
    result = CryptoMarketContextBuilder.global_context(
        {}
    )

    assert result.total_market_cap is None
    assert result.total_volume_24h is None
    assert result.btc_dominance is None
    assert result.data_quality == "MISSING"
