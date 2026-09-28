from urllib.parse import parse_qs, urlparse

from atlas.adapters.etoro_market_data import EtoroMarketDataClient, EtoroCryptoMarketDataProvider
from atlas.market.market_scout import AssetType, MarketObservation
from atlas.services.scanner_service import ScannerService


class FakeCryptoClient:
    def get_instrument_types(self):
        return [
            {"instrumentTypeID": 4, "instrumentTypeDescription": "Stocks"},
            {"instrumentTypeID": 9, "instrumentTypeDescription": "Crypto"},
        ]

    def get_instruments(self, instrument_type_id):
        assert instrument_type_id == 9
        return [
            {"instrumentID": 1, "symbolFull": "BTC", "instrumentDisplayName": "Bitcoin"},
            {"instrumentID": 2, "symbolFull": "ETH", "instrumentDisplayName": "Ethereum"},
        ]

    def get_rates(self, instrument_ids):
        assert instrument_ids == [1, 2]
        return {
            1: {"instrumentID": 1, "lastExecution": 120.0},
            2: {"instrumentID": 2, "lastExecution": 38.0},
        }

    def get_daily_candles(self, instrument_id, count=8):
        assert count == 8
        if instrument_id == 1:
            return [
                {"close": 100.0, "volume": 5.0},
                {"close": 110.0, "volume": 10.0},
                {"close": 115.0, "volume": 20.0},
            ]
        return [
            {"close": 40.0, "volume": 0.0},
            {"close": 39.0, "volume": 0.0},
            {"close": 38.0, "volume": 0.0},
        ]


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return self.body


def test_etoro_provider_builds_crypto_observations_from_full_listing():
    provider = EtoroCryptoMarketDataProvider(FakeCryptoClient())

    observations = provider.get_crypto_observations()

    assert [item.symbol for item in observations] == ["BTC", "ETH"]
    assert all(item.asset_type is AssetType.CRYPTO for item in observations)
    assert abs(observations[0].change_percent - 9.0909) < 0.0001
    assert abs(observations[0].breakout_percent - 20.0) < 0.0001
    assert observations[1].volume == 0.0


def test_crypto_scan_ignores_stock_volume_floor_and_limits_to_100():
    observations = [
        MarketObservation(
            symbol=f"COIN{index:03}",
            asset_type=AssetType.CRYPTO,
            price=1.0,
            volume=0.0,
            average_volume=0.0,
            change_percent=float(index),
        )
        for index in range(125)
    ]

    class Provider:
        def get_crypto_observations(self):
            return observations

    result = ScannerService().scan_crypto(Provider())

    assert result.scanned == 125
    assert result.eligible == 125
    assert len(result.candidates) == 100
    assert result.candidates[0].symbol == "COIN124"
    assert result.candidates[-1].symbol == "COIN025"


def test_etoro_client_batches_rate_requests_at_100_ids():
    requests = []

    def opener(request, timeout):
        requests.append((request, timeout))
        return FakeResponse(b'{"rates": []}')

    client = EtoroMarketDataClient(
        "app-key",
        "user-key",
        opener=opener,
        monotonic=lambda: 1.0,
        sleeper=lambda _: None,
    )
    client.get_rates(list(range(1, 103)))

    assert len(requests) == 2
    first_request = requests[0][0]
    assert first_request.get_header("X-api-key") == "app-key"
    assert first_request.get_header("X-user-key") == "user-key"
    assert first_request.get_header("X-request-id")
    assert parse_qs(urlparse(first_request.full_url).query)["instrumentIds"] == [
        ",".join(str(item) for item in range(1, 101))
    ]


def test_etoro_provider_from_env_requires_both_keys(monkeypatch):
    monkeypatch.setenv("ETORO_API_KEY", "app-key")
    monkeypatch.delenv("ETORO_USER_KEY", raising=False)

    try:
        EtoroCryptoMarketDataProvider.from_env()
    except ValueError as exc:
        assert "ETORO_API_KEY and ETORO_USER_KEY" in str(exc)
    else:
        raise AssertionError("Missing user key should fail clearly")
