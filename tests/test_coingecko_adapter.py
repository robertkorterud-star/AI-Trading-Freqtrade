import io
import json
from urllib.error import HTTPError

from atlas.adapters.coingecko import (
    CoinGeckoAdapter,
)


class FakeResponse:

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        traceback,
    ):
        return False

    def read(self):
        return json.dumps(
            self.payload
        ).encode("utf-8")


def test_get_coin_builds_expected_request():
    requests = []

    def opener(request, timeout):
        requests.append(
            (request, timeout)
        )

        return FakeResponse(
            {
                "id": "bitcoin",
                "symbol": "btc",
            }
        )

    adapter = CoinGeckoAdapter(
        base_url="https://example.test",
        opener=opener,
    )

    result = adapter.get_coin(
        "bitcoin"
    )

    assert result["id"] == "bitcoin"
    assert len(requests) == 1

    request, timeout = requests[0]

    assert (
        request.full_url
        == "https://example.test/coins/bitcoin"
        "?localization=false"
    )

    assert timeout == 10.0


def test_get_markets_uses_market_parameters():
    requests = []

    def opener(request, timeout):
        requests.append(request)

        return FakeResponse([])

    adapter = CoinGeckoAdapter(
        base_url="https://example.test",
        opener=opener,
    )

    result = adapter.get_markets(
        vs_currency="eur",
        page=2,
        per_page=25,
    )

    assert result == []

    url = requests[0].full_url

    assert (
        url.startswith(
            "https://example.test/coins/markets?"
        )
    )

    assert "vs_currency=eur" in url
    assert "page=2" in url
    assert "per_page=25" in url
    assert "sparkline=false" in url


def test_get_market_chart_supports_interval():
    requests = []

    def opener(request, timeout):
        requests.append(request)

        return FakeResponse(
            {
                "prices": [],
                "market_caps": [],
                "total_volumes": [],
            }
        )

    adapter = CoinGeckoAdapter(
        base_url="https://example.test",
        opener=opener,
    )

    result = adapter.get_market_chart(
        "bitcoin",
        vs_currency="usd",
        days=30,
        interval="daily",
    )

    assert "prices" in result

    url = requests[0].full_url

    assert "days=30" in url
    assert "interval=daily" in url


def test_global_categories_and_trending():
    calls = []

    def opener(request, timeout):
        calls.append(request.full_url)

        if request.full_url.endswith(
            "/global"
        ):
            return FakeResponse(
                {"data": {"market_cap": {}}}
            )

        if "/coins/categories" in request.full_url:
            return FakeResponse([])

        return FakeResponse(
            {"coins": []}
        )

    adapter = CoinGeckoAdapter(
        base_url="https://example.test",
        opener=opener,
    )

    assert adapter.get_global_market()[
        "data"
    ]["market_cap"] == {}

    assert adapter.get_categories() == []

    assert adapter.get_trending() == {
        "coins": []
    }

    assert len(calls) == 3


def test_http_errors_are_wrapped():
    def opener(request, timeout):
        raise HTTPError(
            request.full_url,
            429,
            "Too Many Requests",
            {},
            io.BytesIO(
                b'{"error":"rate limit"}'
            ),
        )

    adapter = CoinGeckoAdapter(
        base_url="https://example.test",
        opener=opener,
    )

    try:
        adapter.get_trending()
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "429" in str(exc)
        assert "rate limit" in str(exc)


def test_connection_errors_are_wrapped():
    from urllib.error import URLError

    def opener(request, timeout):
        raise URLError("network unavailable")

    adapter = CoinGeckoAdapter(
        base_url="https://example.test",
        opener=opener,
    )

    try:
        adapter.get_global_market()
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "connection error" in str(exc)
