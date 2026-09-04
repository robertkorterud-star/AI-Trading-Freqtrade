import hashlib
import hmac
from urllib.parse import parse_qs, urlparse

from atlas.execution import (
    BinanceTestnetExecutionAdapter,
    ExecutionRequest,
    ExecutionStatus,
)
from atlas.models.action import Action


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        import json

        return json.dumps(self.payload).encode("utf-8")


def test_binance_testnet_adapter_is_locked_to_testnet() -> None:
    adapter = BinanceTestnetExecutionAdapter("test-key", "test-secret")

    assert adapter.BASE_URL == "https://testnet.binance.vision/api"
    assert "api.binance.com" not in adapter.BASE_URL


def test_binance_testnet_adapter_signs_and_submits_limit_order() -> None:
    captured = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["method"] = request.method
        captured["api_key"] = request.get_header("X-mbx-apikey")
        captured["timeout"] = timeout
        return FakeResponse({"symbol": "BTCUSDT", "orderId": 12345})

    adapter = BinanceTestnetExecutionAdapter(
        "test-key",
        "test-secret",
        opener=opener,
        clock=lambda: 1_700_000_000.0,
    )
    result = adapter.execute(
        ExecutionRequest("BTC/USDT", Action.BUY, 0.01, price=50000.0)
    )

    parsed = urlparse(captured["url"])
    query = parse_qs(parsed.query)
    unsigned = captured["url"].split("&signature=", 1)[0].split("?", 1)[1]
    expected = hmac.new(
        b"test-secret",
        unsigned.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    assert captured["method"] == "POST"
    assert captured["api_key"] == "test-key"
    assert captured["timeout"] == 10.0
    assert parsed.scheme == "https"
    assert parsed.netloc == "testnet.binance.vision"
    assert parsed.path == "/api/v3/order"
    assert query["symbol"] == ["BTCUSDT"]
    assert query["side"] == ["BUY"]
    assert query["type"] == ["LIMIT"]
    assert query["quantity"] == ["0.01"]
    assert query["price"] == ["50000"]
    assert query["timestamp"] == ["1700000000000"]
    assert query["signature"] == [expected]
    assert result.status is ExecutionStatus.ACCEPTED
    assert result.external_order_id == "12345"
    assert result.message == "order submitted to Binance Spot Testnet"


def test_binance_testnet_market_order_uses_testnet_only() -> None:
    captured = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        return FakeResponse({"symbol": "BTCUSDT", "orderId": 99})

    adapter = BinanceTestnetExecutionAdapter(
        "test-key",
        "test-secret",
        opener=opener,
        clock=lambda: 1_700_000_000.0,
    )
    result = adapter.execute(ExecutionRequest("BTC/USDT", Action.SELL, 0.1))

    assert "https://testnet.binance.vision/api/v3/order?" in captured["url"]
    assert "type=MARKET" in captured["url"]
    assert "api.binance.com" not in captured["url"]
    assert result.status is ExecutionStatus.ACCEPTED
    assert result.external_order_id == "99"
