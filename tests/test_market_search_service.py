from atlas.services.market_search_service import MarketSearchService


def test_search_finds_nvidia():
    service = MarketSearchService()

    results = service.search("NVIDIA")

    assert results
    assert results[0]["symbol"] == "NVDA"
    assert results[0]["name"] == "NVIDIA Corporation"
    assert results[0]["type"] == "stock"


def test_search_finds_bitcoin():
    service = MarketSearchService()

    results = service.search("Bitcoin")

    assert results
    assert results[0]["symbol"] == "BTC-USD"
    assert results[0]["type"] == "crypto"


def test_search_finds_by_symbol():
    service = MarketSearchService()

    results = service.search("NVDA")

    assert results
    assert results[0]["symbol"] == "NVDA"


def test_search_is_case_insensitive():
    service = MarketSearchService()

    results = service.search("bitcoin")

    assert results
    assert results[0]["symbol"] == "BTC-USD"


def test_unknown_market_returns_empty():
    service = MarketSearchService()

    assert service.search("DetteFinnesIkke123") == []


def test_search_result_contains_market_data(monkeypatch):
    service = MarketSearchService()

    class FakeMarketData:
        price = 100.0
        previous_close = 95.0
        change_percent = 5.26
        ma20 = 98.0
        ma50 = 92.0

    monkeypatch.setattr(
        service.market,
        "get",
        lambda symbol: FakeMarketData(),
    )

    results = service.search("NVDA")

    assert results
    assert results[0]["price_usd"] == 100.0
    assert results[0]["change"] == 5.26
    assert results[0]["ma20"] == 98.0
    assert results[0]["ma50"] == 92.0
