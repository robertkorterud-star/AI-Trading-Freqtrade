import pytest

from atlas.trading.coingecko_http_client import (
    CoinGeckoHTTPClient,
    CoinGeckoHTTPError,
    CoinGeckoRateLimitError,
    CoinGeckoResponseError,
)


class FakeResponse:

    def __init__(
        self,
        status_code=200,
        payload=None,
    ):
        self.status_code = status_code
        self.payload = payload

    def json(self):
        return self.payload

    def raise_for_status(self):
        return None


class FakeTransport:

    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(
        self,
        url,
        *,
        params,
        timeout,
    ):
        self.calls.append(
            (
                url,
                params,
                timeout,
            )
        )

        return self.response


def _client(response):

    transport = FakeTransport(
        response
    )

    client = CoinGeckoHTTPClient(
        transport=transport,
        timeout=7.5,
    )

    return client, transport


def test_get_ohlc_builds_expected_request():

    client, transport = _client(
        FakeResponse(
            payload=[
                [
                    1767225600000,
                    100,
                    105,
                    99,
                    104,
                ]
            ]
        )
    )

    result = client.get_ohlc(
        coin_id="bitcoin",
        vs_currency="usd",
        days="30",
    )

    assert result == [
        [
            1767225600000.0,
            100.0,
            105.0,
            99.0,
            104.0,
        ]
    ]

    assert transport.calls == [
        (
            "https://api.coingecko.com/api/v3/"
            "coins/bitcoin/ohlc",
            {
                "vs_currency": "usd",
                "days": "30",
            },
            7.5,
        )
    ]


def test_rate_limit_is_explicit():

    client, _ = _client(
        FakeResponse(
            status_code=429
        )
    )

    with pytest.raises(
        CoinGeckoRateLimitError
    ):
        client.get_ohlc(
            "bitcoin",
            "usd",
            "30",
        )


def test_http_failure_is_explicit():

    client, _ = _client(
        FakeResponse(
            status_code=500
        )
    )

    with pytest.raises(
        CoinGeckoHTTPError
    ):
        client.get_ohlc(
            "bitcoin",
            "usd",
            "30",
        )


def test_response_must_be_list():

    client, _ = _client(
        FakeResponse(
            payload={
                "prices": []
            }
        )
    )

    with pytest.raises(
        CoinGeckoResponseError
    ):
        client.get_ohlc(
            "bitcoin",
            "usd",
            "30",
        )


def test_short_ohlc_rows_are_rejected():

    client, _ = _client(
        FakeResponse(
            payload=[
                [
                    1767225600000,
                    100,
                    105,
                ]
            ]
        )
    )

    with pytest.raises(
        CoinGeckoResponseError
    ):
        client.get_ohlc(
            "bitcoin",
            "usd",
            "30",
        )


def test_non_numeric_ohlc_rows_are_rejected():

    client, _ = _client(
        FakeResponse(
            payload=[
                [
                    "timestamp",
                    "open",
                    105,
                    99,
                    104,
                ]
            ]
        )
    )

    with pytest.raises(
        CoinGeckoResponseError
    ):
        client.get_ohlc(
            "bitcoin",
            "usd",
            "30",
        )


def test_empty_coin_id_is_rejected():

    client, _ = _client(
        FakeResponse(payload=[])
    )

    with pytest.raises(ValueError):
        client.get_ohlc(
            "",
            "usd",
            "30",
        )


def test_invalid_timeout_is_rejected():

    transport = FakeTransport(
        FakeResponse(payload=[])
    )

    with pytest.raises(ValueError):
        CoinGeckoHTTPClient(
            transport=transport,
            timeout=0,
        )
