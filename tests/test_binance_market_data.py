import json

import pytest

from atlas.adapters.binance_market_data import (
    BinanceMarketDataAdapter,
)
from atlas.trading.market_data import (
    Candle,
    MarketSnapshot,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def fake_opener(payload):
    def opener(request, timeout):
        assert "api/v3/klines" in request.full_url
        assert "symbol=BTCUSDT" in request.full_url
        assert "interval=1m" in request.full_url
        assert "limit=3" in request.full_url
        assert timeout == 5.0

        return FakeResponse(payload)

    return opener


def sample_payload():
    return [
        [
            1700000000000,
            "50000.0",
            "50100.0",
            "49900.0",
            "50050.0",
            "10.5",
        ],
        [
            1700000060000,
            "50050.0",
            "50200.0",
            "50000.0",
            "50150.0",
            "12.0",
        ],
        [
            1700000120000,
            "50150.0",
            "50300.0",
            "50100.0",
            "50250.0",
            "15.0",
        ],
    ]


def test_binance_candles_are_normalized():
    adapter = BinanceMarketDataAdapter(
        opener=fake_opener(sample_payload()),
        timeout=5.0,
    )

    candles = adapter.get_candles(
        "BTCUSDT",
        interval="1m",
        limit=3,
    )

    assert len(candles) == 3
    assert all(isinstance(candle, Candle) for candle in candles)

    assert candles[0].timestamp == 1700000000.0
    assert candles[0].open == 50000.0
    assert candles[0].high == 50100.0
    assert candles[0].low == 49900.0
    assert candles[0].close == 50050.0
    assert candles[0].volume == 10.5


def test_binance_snapshot_uses_latest_candle():
    adapter = BinanceMarketDataAdapter(
        opener=fake_opener(sample_payload()),
    )

    snapshot = adapter.get_snapshot(
        "BTCUSDT",
        interval="1m",
        limit=3,
    )

    assert isinstance(snapshot, MarketSnapshot)
    assert snapshot.symbol == "BTCUSDT"
    assert snapshot.timestamp == 1700000120.0
    assert snapshot.price == 50250.0
    assert len(snapshot.candles) == 3


def test_binance_get_is_snapshot_alias():
    adapter = BinanceMarketDataAdapter(
        opener=fake_opener(sample_payload()),
    )

    snapshot = adapter.get(
        "BTCUSDT",
        interval="1m",
        limit=3,
    )

    assert isinstance(snapshot, MarketSnapshot)
    assert snapshot.price == 50250.0


def test_invalid_limit_is_rejected():
    adapter = BinanceMarketDataAdapter(
        opener=fake_opener(sample_payload()),
    )

    with pytest.raises(ValueError):
        adapter.get_candles(
            "BTCUSDT",
            limit=0,
        )

    with pytest.raises(ValueError):
        adapter.get_candles(
            "BTCUSDT",
            limit=1001,
        )


def test_empty_binance_response_is_rejected():
    adapter = BinanceMarketDataAdapter(
        opener=fake_opener([]),
    )

    with pytest.raises(ValueError):
        adapter.get_candles("BTCUSDT")


def test_invalid_kline_is_rejected():
    adapter = BinanceMarketDataAdapter(
        opener=fake_opener([[1, 2, 3]]),
    )

    with pytest.raises(ValueError):
        adapter.get_candles("BTCUSDT")
