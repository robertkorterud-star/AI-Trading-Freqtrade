from dataclasses import dataclass

from atlas.services.binance_scanner_service import BinanceScannerService


class FakeAdapter:
    def get_exchange_info(self, symbol=None):
        symbols = [
            {
                "symbol": ticker["symbol"],
                "status": "TRADING",
                "isSpotTradingAllowed": True,
            }
            for ticker in self.tickers
        ]
        if symbol is not None:
            symbols = [
                market for market in symbols
                if market["symbol"] == symbol
            ]
        return {"symbols": symbols}

    def __init__(self, tickers):
        self.tickers = tickers
        self.klines_calls = []

    def get_24hr_tickers(self):
        return self.tickers

    def get_klines(self, symbol, interval="1h", limit=24):
        self.klines_calls.append((symbol, interval, limit))
        return [
            [0, "95", "100", "90", "98", "0", 0, "1000000"]
            for _ in range(limit)
        ]


class MarketData:
    def __init__(self, adapter):
        self.adapter = adapter


@dataclass
class FakeArticle:
    related: tuple[str, ...] = ()
    title: str = ""
    summary: str = ""


class FakeNewsAdapter:
    def __init__(self, articles):
        self.articles = articles
        self.calls = 0

    def latest_crypto_market_news(self):
        self.calls += 1
        return self.articles


class FailingNewsAdapter:
    def latest_crypto_market_news(self):
        raise RuntimeError("news unavailable")


def test_scanner_maps_related_crypto_news_to_binance_pairs():
    tickers = [
        {"symbol": "BTCUSDT", "lastPrice": "100000", "quoteVolume": "500000000", "priceChangePercent": "12"},
        {"symbol": "ETHUSDT", "lastPrice": "4000", "quoteVolume": "300000000", "priceChangePercent": "8"},
        {"symbol": "SOLUSDT", "lastPrice": "200", "quoteVolume": "200000000", "priceChangePercent": "5"},
    ]
    news = FakeNewsAdapter([
        FakeArticle(("BTC",)),
        FakeArticle(("BINANCE:ETHUSDT",)),
    ])

    service = BinanceScannerService(
        MarketData(FakeAdapter(tickers)),
        news_adapter=news,
        volume_enrichment_limit=0,
    )

    observations = service.observations()
    catalysts = {item.symbol: item.news_catalyst for item in observations}

    assert catalysts == {
        "BTCUSDT": True,
        "ETHUSDT": True,
        "SOLUSDT": False,
    }
    assert news.calls == 1


def test_scanner_detects_crypto_catalyst_from_headline_without_related_field():
    tickers = [
        {"symbol": "BTCUSDT", "lastPrice": "100000", "quoteVolume": "500000000", "priceChangePercent": "12"},
        {"symbol": "ETHUSDT", "lastPrice": "4000", "quoteVolume": "300000000", "priceChangePercent": "8"},
        {"symbol": "SOLUSDT", "lastPrice": "200", "quoteVolume": "200000000", "priceChangePercent": "5"},
    ]
    news = FakeNewsAdapter([
        FakeArticle(
            title="Bitcoin surges as institutional demand accelerates",
            summary="Analysts expect stronger BTC flows.",
        ),
    ])

    service = BinanceScannerService(
        MarketData(FakeAdapter(tickers)),
        news_adapter=news,
        volume_enrichment_limit=0,
    )

    observations = service.observations()
    catalysts = {item.symbol: item.news_catalyst for item in observations}

    assert catalysts["BTCUSDT"] is True
    assert catalysts["ETHUSDT"] is False
    assert catalysts["SOLUSDT"] is False


def test_scanner_does_not_match_ticker_as_substring():
    tickers = [
        {"symbol": "SOLUSDT", "lastPrice": "200", "quoteVolume": "200000000", "priceChangePercent": "5"},
    ]
    news = FakeNewsAdapter([
        FakeArticle(title="Consolidation follows broader market weakness"),
    ])

    service = BinanceScannerService(
        MarketData(FakeAdapter(tickers)),
        news_adapter=news,
        volume_enrichment_limit=0,
    )

    observations = service.observations()

    assert observations[0].news_catalyst is False


def test_scanner_catalyst_feed_is_cached_for_one_hour():
    tickers = [
        {"symbol": "BTCUSDT", "lastPrice": "100000", "quoteVolume": "500000000", "priceChangePercent": "12"},
    ]
    news = FakeNewsAdapter([FakeArticle(("BTC",))])
    service = BinanceScannerService(
        MarketData(FakeAdapter(tickers)),
        news_adapter=news,
        volume_enrichment_limit=0,
    )

    first = service.observations()
    second = service.observations()

    assert first[0].news_catalyst is True
    assert second[0].news_catalyst is True
    assert news.calls == 1


def test_scanner_news_failure_keeps_catalyst_false():
    tickers = [
        {"symbol": "BTCUSDT", "lastPrice": "100000", "quoteVolume": "500000000", "priceChangePercent": "12"},
    ]
    service = BinanceScannerService(
        MarketData(FakeAdapter(tickers)),
        news_adapter=FailingNewsAdapter(),
        volume_enrichment_limit=0,
    )

    observations = service.observations()

    assert observations[0].news_catalyst is False
