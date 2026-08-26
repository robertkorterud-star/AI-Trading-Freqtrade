from datetime import datetime, timedelta, timezone

import pytest

from atlas.trading.coingecko_historical_data import (
    CoinGeckoHistoricalDataProvider,
)


class FakeCoinGeckoClient:

    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get_market_chart(
        self,
        coin_id,
        vs_currency,
        days,
    ):
        self.calls.append(
            (
                coin_id,
                vs_currency,
                days,
            )
        )

        return self.payload


def _payload():

    return {
        "prices": [
            [1767225600000, 100.0],
            [1767312000000, 105.0],
            [1767398400000, 110.0],
        ],
        "total_volumes": [
            [1767225600000, 1000.0],
            [1767312000000, 1200.0],
            [1767398400000, 1400.0],
        ],
    }


def test_coingecko_provider_returns_market_data():

    client = FakeCoinGeckoClient(
        _payload()
    )

    provider = CoinGeckoHistoricalDataProvider(
        client=client,
        coin_ids={
            "BTC-USD": "bitcoin",
        },
    )

    result = provider.load(
        symbol="BTC-USD",
    )

    assert result.symbol == "BTC-USD"
    assert len(result) == 3
    assert result.closes == [
        100.0,
        105.0,
        110.0,
    ]


def test_coingecko_symbol_mapping_is_used():

    client = FakeCoinGeckoClient(
        _payload()
    )

    provider = CoinGeckoHistoricalDataProvider(
        client=client,
        coin_ids={
            "BTC-USD": "bitcoin",
        },
    )

    provider.load(
        symbol="BTC-USD",
    )

    assert client.calls == [
        (
            "bitcoin",
            "usd",
            "30",
        )
    ]


def test_coingecko_default_symbol_mapping():

    client = FakeCoinGeckoClient(
        _payload()
    )

    provider = CoinGeckoHistoricalDataProvider(
        client=client,
    )

    provider.load(
        symbol="ethereum",
    )

    assert client.calls[0][0] == "ethereum"


def test_coingecko_volume_is_preserved():

    client = FakeCoinGeckoClient(
        _payload()
    )

    provider = CoinGeckoHistoricalDataProvider(
        client=client,
    )

    result = provider.load(
        symbol="bitcoin",
    )

    assert [
        bar.volume
        for bar in result.bars
    ] == [
        1000.0,
        1200.0,
        1400.0,
    ]


def test_invalid_date_range_is_rejected():

    client = FakeCoinGeckoClient(
        _payload()
    )

    provider = CoinGeckoHistoricalDataProvider(
        client=client,
    )

    start = datetime(
        2026,
        1,
        10,
        tzinfo=timezone.utc,
    )

    end = start - timedelta(
        days=1
    )

    with pytest.raises(ValueError):
        provider.load(
            symbol="bitcoin",
            start=start,
            end=end,
        )
