import json
from datetime import datetime, timedelta, timezone

from urllib.parse import parse_qs, urlparse

from atlas.adapters.etoro_market_data import EtoroMarketDataClient, EtoroCryptoMarketDataProvider
from atlas.market.market_scout import AssetType, MarketObservation
from atlas.services.scanner_service import ScannerService


def instrument(instrument_id, symbol, **overrides):
    return {
        "instrumentId": instrument_id, "internalSymbolFull": symbol,
        "displayname": symbol, "instrumentTypeID": 9,
        "isActiveInPlatform": True, "isCurrentlyTradable": True,
        "isBuyEnabled": True, "isDelisted": False,
        "isHiddenFromClient": False, "isInternalInstrument": False,
        **overrides,
    }


class FakeCryptoClient:
    def get_instrument_types(self):
        return [
            {"instrumentTypeID": 4, "instrumentTypeDescription": "Stocks"},
            {"instrumentTypeID": 9, "instrumentTypeDescription": "Crypto"},
        ]

    def get_instruments(self, instrument_type_id):
        assert instrument_type_id == 9
        return [
            instrument(1, "BTC"),
            instrument(2, "ETH"),
        ]

    def get_rates(self, instrument_ids):
        assert instrument_ids == [1, 2]
        return {
            1: {"instrumentID": 1, "bid": 119.5, "ask": 120.5,
                "date": datetime.now(timezone.utc).isoformat()},
            2: {"instrumentID": 2, "bid": 37.9, "ask": 38.1,
                "date": datetime.now(timezone.utc).isoformat()},
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
    assert observations[0].breakout_percent == 0.0
    assert abs(observations[0].bid_ask_spread_percent - 100 / 120) < 0.0001
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


def test_etoro_provider_loads_dotenv_and_requires_both_keys(
    tmp_path,
    monkeypatch,
):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ETORO_API_KEY=app-key\nETORO_USER_KEY='user-key'\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("ETORO_API_KEY", raising=False)
    monkeypatch.delenv("ETORO_USER_KEY", raising=False)

    provider = EtoroCryptoMarketDataProvider.from_env(env_file=env_file)

    assert provider.client.api_key == "app-key"
    assert provider.client.user_key == "user-key"

    incomplete_env = tmp_path / "incomplete.env"
    incomplete_env.write_text("ETORO_API_KEY=app-key\n", encoding="utf-8")
    monkeypatch.delenv("ETORO_API_KEY", raising=False)
    monkeypatch.delenv("ETORO_USER_KEY", raising=False)
    try:
        EtoroCryptoMarketDataProvider.from_env(env_file=incomplete_env)
    except ValueError as exc:
        assert "ETORO_API_KEY and ETORO_USER_KEY" in str(exc)
    else:
        raise AssertionError("Missing user key should fail clearly")


def test_etoro_filters_status_before_fetching_rates_or_candles():
    class Client(FakeCryptoClient):
        def get_instruments(self, instrument_type_id):
            valid = super().get_instruments(instrument_type_id)
            invalid = [
                instrument(3, "BIGTIME.old"),
                instrument(4, "BADGER.OLD"),
                instrument(5, "STOCK", instrumentTypeID=4),
            ]
            for key in ("isActiveInPlatform", "isCurrentlyTradable", "isBuyEnabled"):
                invalid.append(instrument(10 + len(invalid), key, **{key: False}))
            for key in ("isDelisted", "isHiddenFromClient", "isInternalInstrument"):
                invalid.append(instrument(10 + len(invalid), key, **{key: True}))
            for key in ("isActiveInPlatform", "isCurrentlyTradable", "isBuyEnabled",
                        "isDelisted", "isHiddenFromClient", "isInternalInstrument"):
                missing = instrument(10 + len(invalid), "MISSING")
                del missing[key]
                invalid.append(missing)
            invalid.append(instrument(99, "STRING", isBuyEnabled="false"))
            return valid + invalid

        def get_daily_candles(self, instrument_id, count=8):
            assert instrument_id in (1, 2)
            return super().get_daily_candles(instrument_id, count)

    result = ScannerService().scan_crypto(EtoroCryptoMarketDataProvider(Client()))
    assert {item.symbol for item in result.candidates} == {"BTC", "ETH"}


def test_etoro_search_reads_all_pages_and_requests_status():
    queries = []

    def opener(request, timeout):
        query = parse_qs(urlparse(request.full_url).query)
        queries.append(query)
        assert urlparse(request.full_url).path.endswith("/market-data/search")
        page = int(query.get("page", ["1"])[0])
        # Server may use smaller pages than requested.
        return FakeResponse(json.dumps({
            "items": [instrument(page, f"COIN{page}")],
            "totalItems": 3, "pageSize": 1, "page": page,
        }).encode())

    client = EtoroMarketDataClient("app", "user", opener=opener,
                                  sleeper=lambda _: None)
    items = client._get_instrument_statuses()
    assert [item["instrumentId"] for item in items] == [1, 2, 3]
    assert [query["page"] for query in queries] == [["1"], ["2"], ["3"]]
    assert "isDelisted" in queries[0]["fields"][0]
    assert "isCurrentlyTradable" in queries[0]["fields"][0]


def test_etoro_search_rejects_incomplete_or_repeated_pages():
    for response in (
        {"items": [], "totalItems": 2, "page": 1},
        {"items": [instrument(1, "BTC")], "totalItems": 2, "page": 1},
        {"instrumentDisplayDatas": []},
    ):
        client = EtoroMarketDataClient(
            "app", "user", sleeper=lambda _: None,
            opener=lambda request, timeout: FakeResponse(json.dumps(response).encode()),
        )
        try:
            client._get_instrument_statuses()
        except RuntimeError:
            pass
        else:
            raise AssertionError("Incomplete universe must fail explicitly")


def test_etoro_joins_status_to_display_catalog_when_search_omits_type():
    def opener(request, timeout):
        path = urlparse(request.full_url).path
        if path.endswith("/market-data/instruments"):
            payload = {"instrumentDisplayDatas": [
                {"instrumentID": 1, "instrumentTypeID": 9, "symbolFull": "BTC",
                 "instrumentDisplayName": "Bitcoin", "isInternalInstrument": False},
                # Even if the server ignores the type filter, exclude stocks.
                {"instrumentID": 2, "instrumentTypeID": 4, "symbolFull": "STOCK",
                 "isInternalInstrument": False},
            ]}
        else:
            crypto = instrument(1, "SEARCH_SYMBOL")
            del crypto["instrumentTypeID"]
            stock = instrument(2, "STOCK")
            del stock["instrumentTypeID"]
            payload = {"page": 1, "totalItems": 3, "items": [
                {"instrumentId": -100000}, crypto, stock,
            ]}
        return FakeResponse(json.dumps(payload).encode())

    client = EtoroMarketDataClient("app", "user", opener=opener,
                                  sleeper=lambda _: None)
    items = client.get_instruments(9)
    assert len(items) == 1
    assert items[0]["instrumentId"] == 1
    assert items[0]["instrumentTypeID"] == 9
    assert items[0]["internalSymbolFull"] == "BTC"
    assert items[0]["isActiveInPlatform"] is True


def test_etoro_rejects_bad_quotes_before_candle_requests():
    now = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)
    valid = {"bid": 99.5, "ask": 100.5, "date": now.isoformat()}
    invalid = [
        {**valid, "bid": None}, {**valid, "ask": 0},
        {**valid, "bid": -1}, {**valid, "bid": 101},
        {**valid, "ask": float("inf")}, {**valid, "bid": float("nan")},
        {**valid, "ask": 110}, {**valid, "date": None},
        {**valid, "date": "2026-09-28T12:00:00"},
        {**valid, "date": (now - timedelta(seconds=301)).isoformat()},
        {**valid, "date": (now + timedelta(seconds=31)).isoformat()},
    ]
    for quote in invalid:
        class Client(FakeCryptoClient):
            def get_rates(self, ids):
                return {1: quote}

            def get_daily_candles(self, *args):
                raise AssertionError("Rejected quote must not fetch candles")

        provider = EtoroCryptoMarketDataProvider(Client(), now=lambda: now)
        assert provider.get_crypto_observations() == []


def test_etoro_spread_limit_is_configurable_and_uses_midpoint():
    now = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)
    class Client(FakeCryptoClient):
        def get_rates(self, ids):
            return {1: {"bid": 99, "ask": 101, "lastExecution": 999,
                        "date": now.isoformat()}}
    accepted = EtoroCryptoMarketDataProvider(Client(), now=lambda: now)
    observations = accepted.get_crypto_observations()
    assert len(observations) == 1
    assert observations[0].price == 100
    assert observations[0].bid_ask_spread_percent == 2
    rejected = EtoroCryptoMarketDataProvider(Client(), max_spread_percent=1.9,
                                            now=lambda: now)
    assert rejected.get_crypto_observations() == []


def test_etoro_invalid_history_cannot_create_momentum_candidate():
    for history in ([], [{"close": 100}], [{"close": 0}, {"close": 110}],
                    [{"close": float("inf")}, {"close": 110}]):
        class Client(FakeCryptoClient):
            def get_daily_candles(self, *args):
                return history
        assert EtoroCryptoMarketDataProvider(Client()).get_crypto_observations() == []


def test_etoro_candle_api_failure_is_not_a_silent_partial_scan():
    class Client(FakeCryptoClient):
        def get_daily_candles(self, *args):
            raise RuntimeError("eToro API rate limit reached (HTTP 429).")
    try:
        EtoroCryptoMarketDataProvider(Client()).get_crypto_observations()
    except RuntimeError as exc:
        assert "429" in str(exc)
    else:
        raise AssertionError("API failure must remain visible")


def test_scout_prefers_narrow_spread_without_inventing_volume():
    from atlas.market.market_scout import MarketScout
    common = dict(asset_type=AssetType.CRYPTO, price=100, volume=0,
                  average_volume=0, change_percent=5)
    ranked = MarketScout().scan([
        MarketObservation(symbol="WIDE", bid_ask_spread_percent=2, **common),
        MarketObservation(symbol="NARROW", bid_ask_spread_percent=0.2, **common),
    ])
    assert [item.symbol for item in ranked] == ["NARROW", "WIDE"]
    assert ranked[0].volume_score == 0
    assert ranked[0].liquidity_score > ranked[1].liquidity_score
    assert "quoted spread 0.200%" in ranked[0].reasons


def test_etoro_quote_limits_reject_invalid_configuration():
    for limit in (0, -1, float("nan"), float("inf")):
        try:
            EtoroCryptoMarketDataProvider(FakeCryptoClient(), max_spread_percent=limit)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid spread limit should fail")
