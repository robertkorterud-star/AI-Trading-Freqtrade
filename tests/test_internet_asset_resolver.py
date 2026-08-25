from atlas.market.asset_type import AssetType
from atlas.services.internet_asset_resolver import (
    InternetAssetResolver,
)


class FakeSearchClient:
    def search(self, query):
        return [
            {
                "symbol": "PLTR",
                "shortname": "Palantir Technologies",
                "longname": "Palantir Technologies Inc.",
                "quoteType": "EQUITY",
                "exchange": "NMS",
                "currency": "USD",
            }
        ]


def test_resolver_finds_stock_from_internet_result():

    resolver = InternetAssetResolver(
        search_client=FakeSearchClient()
    )

    results = resolver.resolve("Palantir")

    assert len(results) == 1

    asset = results[0]

    assert asset.symbol == "PLTR"
    assert asset.name == "Palantir Technologies Inc."
    assert asset.asset_type == AssetType.STOCK
    assert asset.currency == "USD"


def test_resolver_maps_crypto_result():

    class FakeCryptoSearch:

        def search(self, query):
            return [
                {
                    "symbol": "XRP-USD",
                    "shortname": "XRP USD",
                    "longname": "XRP",
                    "quoteType": "CRYPTOCURRENCY",
                    "exchange": "CCC",
                    "currency": "USD",
                }
            ]

    resolver = InternetAssetResolver(
        search_client=FakeCryptoSearch()
    )

    results = resolver.resolve("Ripple")

    assert results[0].symbol == "XRP-USD"
    assert results[0].asset_type == AssetType.CRYPTO


def test_resolver_maps_etf_result():

    class FakeETFSearch:

        def search(self, query):
            return [
                {
                    "symbol": "QQQ",
                    "shortname": "Invesco QQQ",
                    "longname": "Invesco QQQ Trust",
                    "quoteType": "ETF",
                    "exchange": "NMS",
                    "currency": "USD",
                }
            ]

    resolver = InternetAssetResolver(
        search_client=FakeETFSearch()
    )

    results = resolver.resolve("QQQ")

    assert results[0].symbol == "QQQ"
    assert results[0].asset_type == AssetType.ETF


def test_resolver_ignores_unsupported_quote_types():

    class FakeSearch:

        def search(self, query):
            return [
                {
                    "symbol": "TEST",
                    "shortname": "Unsupported",
                    "longname": "Unsupported Asset",
                    "quoteType": "MUTUALFUND",
                    "exchange": "NMS",
                    "currency": "USD",
                }
            ]

    resolver = InternetAssetResolver(
        search_client=FakeSearch()
    )

    assert resolver.resolve("Unsupported") == []


def test_resolver_handles_empty_query():

    resolver = InternetAssetResolver(
        search_client=FakeSearchClient()
    )

    assert resolver.resolve("   ") == []
