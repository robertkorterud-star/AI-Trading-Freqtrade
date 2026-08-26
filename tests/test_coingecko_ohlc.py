from datetime import datetime, timezone

import pytest

from atlas.trading.coingecko_ohlc import (
    CoinGeckoOHLCProvider,
)


class FakeCoinGeckoOHLCClient:

    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def get_ohlc(
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

        return self.rows


def _rows():

    return [
        [
            1767225600000,
            100.0,
            105.0,
            99.0,
            104.0,
        ],
        [
            1767312000000,
            104.0,
            110.0,
            103.0,
            108.0,
        ],
        [
            1767398400000,
            108.0,
            112.0,
            107.0,
            111.0,
        ],
    ]


def test_ohlc_provider_preserves_real_candles():

    client = FakeCoinGeckoOHLCClient(
        _rows()
    )

    provider = CoinGeckoOHLCProvider(
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

    first = result.bars[0]

    assert first.open == 100.0
    assert first.high == 105.0
    assert first.low == 99.0
    assert first.close == 104.0


def test_ohlc_provider_uses_utc_timestamps():

    client = FakeCoinGeckoOHLCClient(
        _rows()
    )

    provider = CoinGeckoOHLCProvider(
        client=client,
    )

    result = provider.load(
        symbol="bitcoin",
    )

    assert (
        result.bars[0].timestamp.tzinfo
        == timezone.utc
    )


def test_ohlc_provider_maps_symbol():

    client = FakeCoinGeckoOHLCClient(
        _rows()
    )

    provider = CoinGeckoOHLCProvider(
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


def test_ohlc_provider_has_no_fake_volume():

    client = FakeCoinGeckoOHLCClient(
        _rows()
    )

    provider = CoinGeckoOHLCProvider(
        client=client,
    )

    result = provider.load(
        symbol="bitcoin",
    )

    assert [
        bar.volume
        for bar in result.bars
    ] == [
        0.0,
        0.0,
        0.0,
    ]


def test_ohlc_provider_rejects_short_rows():

    client = FakeCoinGeckoOHLCClient(
        [
            [
                1767225600000,
                100.0,
                105.0,
            ]
        ]
    )

    provider = CoinGeckoOHLCProvider(
        client=client,
    )

    with pytest.raises(ValueError):
        provider.load(
            symbol="bitcoin",
        )


def test_ohlc_provider_rejects_invalid_date_range():

    client = FakeCoinGeckoOHLCClient(
        _rows()
    )

    provider = CoinGeckoOHLCProvider(
        client=client,
    )

    start = datetime(
        2026,
        1,
        10,
        tzinfo=timezone.utc,
    )

    end = datetime(
        2026,
        1,
        9,
        tzinfo=timezone.utc,
    )

    with pytest.raises(ValueError):
        provider.load(
            symbol="bitcoin",
            start=start,
            end=end,
        )


def test_ohlc_provider_accepts_real_http_client_contract():

    from atlas.trading.coingecko_http_client import (
        CoinGeckoHTTPClient,
    )

    class FakeResponse:

        status_code = 200

        def json(self):
            return [
                [
                    1767225600000,
                    100.0,
                    105.0,
                    99.0,
                    104.0,
                ],
                [
                    1767312000000,
                    104.0,
                    110.0,
                    103.0,
                    108.0,
                ],
            ]

    class FakeTransport:

        def get(
            self,
            url,
            *,
            params,
            timeout,
        ):
            return FakeResponse()

    client = CoinGeckoHTTPClient(
        transport=FakeTransport(),
    )

    provider = CoinGeckoOHLCProvider(
        client=client,
        coin_ids={
            "BTC-USD": "bitcoin",
        },
    )

    result = provider.load(
        symbol="BTC-USD",
    )

    assert result.symbol == "BTC-USD"
    assert len(result) == 2

    assert result.bars[0].open == 100.0
    assert result.bars[0].high == 105.0
    assert result.bars[0].low == 99.0
    assert result.bars[0].close == 104.0


def test_ohlc_provider_preserves_timeframe_and_source():

    client = FakeCoinGeckoOHLCClient(
        _rows()
    )

    provider = CoinGeckoOHLCProvider(
        client=client,
        coin_ids={
            "BTC-USD": "bitcoin",
        },
        timeframe="4h",
        source="coingecko",
    )

    result = provider.load(
        symbol="BTC-USD",
    )

    assert result.timeframe == "4h"
    assert result.source == "coingecko"


def test_ohlc_provider_supports_explicit_timeframe():

    client = FakeCoinGeckoOHLCClient(
        _rows()
    )

    provider = CoinGeckoOHLCProvider(
        client=client,
        timeframe="1h",
    )

    result = provider.load(
        symbol="bitcoin",
    )

    assert result.timeframe == "1h"
