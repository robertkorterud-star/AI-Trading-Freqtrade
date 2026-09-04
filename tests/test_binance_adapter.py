import json

import pytest

from atlas.adapters.binance import BinanceAdapter


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.payload


class RecordingOpener:
    def __init__(self, payload):
        self.payload = payload
        self.request = None
        self.timeout = None

    def __call__(self, request, timeout):
        self.request = request
        self.timeout = timeout
        return FakeResponse(self.payload)


def test_default_endpoint_is_binance_public_market_data_only():
    adapter = BinanceAdapter(
        opener=RecordingOpener({"symbol": "BTCUSDT", "price": "100000.00"})
    )

    assert adapter.BASE_URL == "https://data-api.binance.vision/api/v3"
    assert adapter.base_url == adapter.BASE_URL


def test_get_price_builds_public_request():
    opener = RecordingOpener({"symbol": "BTCUSDT", "price": "100000.00"})
    adapter = BinanceAdapter(
        base_url="https://example.test/api/v3",
        timeout=3.5,
        opener=opener,
    )

    result = adapter.get_price("BTCUSDT")

    assert result["symbol"] == "BTCUSDT"
    assert "symbol=BTCUSDT" in opener.request.full_url
    assert opener.request.get_method() == "GET"
    assert opener.timeout == 3.5


def test_get_klines_sends_market_parameters():
    opener = RecordingOpener([])
    adapter = BinanceAdapter(
        base_url="https://example.test/api/v3",
        opener=opener,
    )

    adapter.get_klines(
        "ETHUSDT",
        interval="5m",
        limit=100,
        start_time=1000,
        end_time=2000,
    )

    url = opener.request.full_url
    assert "symbol=ETHUSDT" in url
    assert "interval=5m" in url
    assert "limit=100" in url
    assert "startTime=1000" in url
    assert "endTime=2000" in url


def test_get_order_book_is_read_only_get():
    opener = RecordingOpener({"lastUpdateId": 1, "bids": [], "asks": []})
    adapter = BinanceAdapter(
        base_url="https://example.test/api/v3",
        opener=opener,
    )

    result = adapter.get_order_book("BTCUSDT", limit=20)

    assert result["lastUpdateId"] == 1
    assert opener.request.get_method() == "GET"
    assert "limit=20" in opener.request.full_url


def test_get_recent_trades():
    opener = RecordingOpener([{"id": 1, "price": "100.0"}])
    adapter = BinanceAdapter(
        base_url="https://example.test/api/v3",
        opener=opener,
    )

    result = adapter.get_recent_trades("BTCUSDT", limit=50)

    assert result[0]["id"] == 1
    assert "limit=50" in opener.request.full_url


def test_get_exchange_info_can_target_symbol():
    opener = RecordingOpener({"symbols": []})
    adapter = BinanceAdapter(
        base_url="https://example.test/api/v3",
        opener=opener,
    )

    adapter.get_exchange_info("BTCUSDT")

    assert "symbol=BTCUSDT" in opener.request.full_url


def test_invalid_json_is_reported():
    class InvalidResponse(FakeResponse):
        def read(self):
            return b"not-json"

    class InvalidOpener(RecordingOpener):
        def __call__(self, request, timeout):
            self.request = request
            self.timeout = timeout
            return InvalidResponse(None)

    adapter = BinanceAdapter(
        base_url="https://example.test/api/v3",
        opener=InvalidOpener(None),
    )

    with pytest.raises(RuntimeError, match="invalid JSON"):
        adapter.get_price("BTCUSDT")
