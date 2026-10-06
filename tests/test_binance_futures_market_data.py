from atlas.adapters.binance_futures import BinanceFuturesAdapter


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.payload


def test_funding_rate_history_uses_usdm_public_endpoint():
    requests = []

    def opener(request, timeout):
        requests.append((request, timeout))
        return FakeResponse(
            b'[{"symbol":"BTCUSDT","fundingRate":"0.00010000",'
            b'"fundingTime":1767225600000,"markPrice":"93450.0"}]'
        )

    adapter = BinanceFuturesAdapter(opener=opener)

    result = adapter.get_funding_rate_history(
        symbol="BTCUSDT",
        start_time=1767225600000,
        end_time=1767312000000,
        limit=100,
    )

    assert result[0]["symbol"] == "BTCUSDT"
    assert result[0]["fundingRate"] == "0.00010000"

    request, timeout = requests[0]
    assert request.full_url.startswith(
        "https://fapi.binance.com/fapi/v1/fundingRate?"
    )
    assert "symbol=BTCUSDT" in request.full_url
    assert "startTime=1767225600000" in request.full_url
    assert "endTime=1767312000000" in request.full_url
    assert "limit=100" in request.full_url
    assert timeout == 10.0


def test_open_interest_history_uses_usdm_public_endpoint():
    requests = []

    def opener(request, timeout):
        requests.append((request, timeout))
        return FakeResponse(
            b'[{"symbol":"BTCUSDT","sumOpenInterest":"12345.0",'
            b'"sumOpenInterestValue":"1150000000.0",'
            b'"timestamp":1767225600000}]'
        )

    adapter = BinanceFuturesAdapter(opener=opener)

    result = adapter.get_open_interest_history(
        symbol="BTCUSDT",
        period="5m",
        start_time=1767225600000,
        end_time=1767312000000,
        limit=100,
    )

    assert result[0]["symbol"] == "BTCUSDT"
    assert result[0]["sumOpenInterest"] == "12345.0"

    request, timeout = requests[0]
    assert request.full_url.startswith(
        "https://fapi.binance.com/futures/data/openInterestHist?"
    )
    assert "symbol=BTCUSDT" in request.full_url
    assert "period=5m" in request.full_url
    assert "startTime=1767225600000" in request.full_url
    assert "endTime=1767312000000" in request.full_url
    assert "limit=100" in request.full_url
    assert timeout == 10.0


def test_klines_use_usdm_public_endpoint():
    requests = []

    def opener(request, timeout):
        requests.append((request, timeout))
        return FakeResponse(
            b'[[1791279000000,"86200.0","86250.0","86180.0",'
            b'"86230.0","123.45",1791279059999,"10640000.0",'
            b'321,"78.90","6800000.0","0"]]'
        )

    adapter = BinanceFuturesAdapter(opener=opener)

    result = adapter.get_klines(
        symbol="BTCUSDT",
        interval="1m",
        start_time=1791279000000,
        end_time=1791279060000,
        limit=500,
    )

    assert result[0][0] == 1791279000000
    assert result[0][5] == "123.45"
    assert result[0][9] == "78.90"

    request, timeout = requests[0]

    assert request.full_url.startswith(
        "https://fapi.binance.com/fapi/v1/klines?"
    )
    assert "symbol=BTCUSDT" in request.full_url
    assert "interval=1m" in request.full_url
    assert "startTime=1791279000000" in request.full_url
    assert "endTime=1791279060000" in request.full_url
    assert "limit=500" in request.full_url
    assert timeout == 10.0
