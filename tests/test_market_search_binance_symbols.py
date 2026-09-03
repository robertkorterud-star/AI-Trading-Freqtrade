from atlas.services.market_search_service import MarketSearchService


def test_market_search_resolves_binance_usdt_symbol_without_catalog_lookup(monkeypatch):
    service = MarketSearchService()
    monkeypatch.setattr(
        service.internet_resolver,
        "resolve",
        lambda _: (_ for _ in ()).throw(AssertionError("resolver should not be called")),
    )

    results = service.search("SOLUSDT")

    assert results == [
        {
            "symbol": "SOLUSDT",
            "name": "SOL",
            "type": "crypto",
            "market": "Binance",
            "currency": "USDT",
            "price_usd": None,
            "change": None,
            "ma20": None,
            "ma50": None,
        }
    ]


def test_market_search_resolves_binance_usdc_symbol_case_insensitively(monkeypatch):
    service = MarketSearchService()
    monkeypatch.setattr(
        service.internet_resolver,
        "resolve",
        lambda _: (_ for _ in ()).throw(AssertionError("resolver should not be called")),
    )

    result = service.search("ethusdc")[0]

    assert result["symbol"] == "ETHUSDC"
    assert result["type"] == "crypto"
    assert result["market"] == "Binance"
    assert result["currency"] == "USDC"
