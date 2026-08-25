from atlas.services.yfinance_search_client import (
    YFinanceSearchClient,
)


def test_yfinance_search_client_maps_quotes(monkeypatch):

    class FakeSearch:

        def __init__(self, query):
            self.quotes = [
                {
                    "symbol": "PLTR",
                    "shortname": "Palantir",
                    "longname": "Palantir Technologies Inc.",
                    "quoteType": "EQUITY",
                    "exchange": "NMS",
                    "currency": "USD",
                }
            ]

    monkeypatch.setattr(
        "yfinance.Search",
        FakeSearch,
    )

    client = YFinanceSearchClient()

    results = client.search("Palantir")

    assert results[0]["symbol"] == "PLTR"
    assert results[0]["quoteType"] == "EQUITY"


def test_yfinance_search_client_returns_empty_when_no_quotes(
    monkeypatch,
):

    class FakeSearch:

        def __init__(self, query):
            self.quotes = []

    monkeypatch.setattr(
        "yfinance.Search",
        FakeSearch,
    )

    client = YFinanceSearchClient()

    assert client.search("does-not-exist") == []
