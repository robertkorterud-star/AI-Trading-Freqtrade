from atlas.news.alpha_vantage import AlphaVantageNewsAdapter
from atlas.news.source_manager import NewsSourceManager


class FakeClock:
    def __init__(self, value=0.0):
        self.value = value

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class SpySource:
    def __init__(self, articles):
        self.articles = articles
        self.calls = 0

    def fetch(self, symbol):
        self.calls += 1
        return list(self.articles)


def test_alpha_vantage_symbol_mapping():
    assert AlphaVantageNewsAdapter.ticker_for_symbol("AAPL") == "AAPL"
    assert AlphaVantageNewsAdapter.ticker_for_symbol("NVDA") == "NVDA"
    assert AlphaVantageNewsAdapter.ticker_for_symbol("BTC-USD") == "CRYPTO:BTC"
    assert AlphaVantageNewsAdapter.ticker_for_symbol("ETH-USD") == "CRYPTO:ETH"
    assert AlphaVantageNewsAdapter.ticker_for_symbol("SOL-USD") == "CRYPTO:SOL"
    assert AlphaVantageNewsAdapter.ticker_for_symbol("XRP-USD") == "CRYPTO:XRP"
    assert AlphaVantageNewsAdapter.ticker_for_symbol("UNKNOWN") is None


def test_alpha_vantage_missing_key_is_nonfatal(monkeypatch):
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)

    adapter = AlphaVantageNewsAdapter()

    assert adapter.search("AAPL") == []


def test_alpha_vantage_normalizes_news(monkeypatch):
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "test-key")

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "feed": [
                    {
                        "title": "Apple reports strong results",
                        "source": "Example News",
                        "summary": "Apple had a strong quarter.",
                        "url": "https://example.com/apple",
                        "overall_sentiment_label": "Bullish",
                        "time_published": "20260914100000",
                    }
                ]
            }

    captured = {}

    def fake_get(url, params, timeout):
        captured["url"] = url
        captured["params"] = params
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(
        "atlas.news.alpha_vantage.requests.get",
        fake_get,
    )

    adapter = AlphaVantageNewsAdapter()
    result = adapter.search("AAPL")

    assert captured["params"]["function"] == "NEWS_SENTIMENT"
    assert captured["params"]["tickers"] == "AAPL"
    assert result == [
        {
            "title": "Apple reports strong results",
            "source": "Example News",
            "summary": "Apple had a strong quarter.",
            "url": "https://example.com/apple",
            "sentiment": "positive",
            "published_at": "20260914100000",
        }
    ]


def test_manager_caches_each_source_with_its_own_freshness():
    clock = FakeClock()

    alpha = SpySource(
        [
            {
                "title": "Alpha article",
                "source": "Alpha",
                "url": "https://example.com/alpha",
                "published_at": "1",
            }
        ]
    )
    finnhub = SpySource(
        [
            {
                "title": "Finnhub article",
                "source": "Finnhub",
                "url": "https://example.com/finnhub",
                "published_at": "1",
            }
        ]
    )

    manager = NewsSourceManager(
        sources={
            "alpha_vantage": alpha,
            "finnhub": finnhub,
        },
        clock=clock,
    )

    first = manager.latest("AAPL")
    second = manager.latest("AAPL")

    assert len(first) == 2
    assert second == first
    assert alpha.calls == 1
    assert finnhub.calls == 1

    clock.advance(10 * 60)

    third = manager.latest("AAPL")

    assert len(third) == 2
    assert alpha.calls == 2
    assert finnhub.calls == 2


def test_manager_deduplicates_by_url():
    source_a = SpySource(
        [
            {
                "title": "Same article",
                "source": "Source A",
                "url": "https://example.com/same",
                "published_at": "1",
            }
        ]
    )
    source_b = SpySource(
        [
            {
                "title": "Same article with another title",
                "source": "Source B",
                "url": "https://example.com/same",
                "published_at": "2",
            }
        ]
    )

    manager = NewsSourceManager(
        sources={
            "alpha_vantage": source_a,
            "finnhub": source_b,
        }
    )

    result = manager.latest("AAPL")

    assert len(result) == 1
    assert result[0]["url"] == "https://example.com/same"


def test_manager_deduplicates_without_url():
    source = SpySource(
        [
            {
                "title": "Same title",
                "source": "Example",
                "summary": "First",
                "published_at": "20260914100000",
            },
            {
                "title": "Same title",
                "source": "Example",
                "summary": "Duplicate",
                "published_at": "20260914100000",
            },
        ]
    )

    manager = NewsSourceManager(
        sources={"alpha_vantage": source}
    )

    result = manager.latest("AAPL")

    assert len(result) == 1
    assert result[0]["summary"] == "First"


def test_manager_keeps_same_article_from_different_sources():
    source_a = SpySource(
        [
            {
                "title": "Market moves higher",
                "source": "Source A",
                "published_at": "20260914100000",
            }
        ]
    )
    source_b = SpySource(
        [
            {
                "title": "Market moves higher",
                "source": "Source B",
                "published_at": "20260914100000",
            }
        ]
    )

    manager = NewsSourceManager(
        sources={
            "alpha_vantage": source_a,
            "finnhub": source_b,
        }
    )

    result = manager.latest("AAPL")

    assert len(result) == 2


def test_manager_aggregates_fallback_sources():
    alpha = SpySource([])
    finnhub = SpySource(
        [
            {
                "title": "Finnhub fallback",
                "source": "Finnhub",
                "url": "https://example.com/fallback",
                "published_at": "1",
            }
        ]
    )

    manager = NewsSourceManager(
        sources={
            "alpha_vantage": alpha,
            "finnhub": finnhub,
        }
    )

    result = manager.latest("AAPL")

    assert result[0]["title"] == "Finnhub fallback"


def test_manager_handles_source_failure():
    class BrokenSource:
        def fetch(self, symbol):
            raise RuntimeError("temporary failure")

    healthy = SpySource(
        [
            {
                "title": "Healthy article",
                "source": "Healthy",
                "url": "https://example.com/healthy",
                "published_at": "1",
            }
        ]
    )

    manager = NewsSourceManager(
        sources={
            "alpha_vantage": BrokenSource(),
            "finnhub": healthy,
        }
    )

    result = manager.latest("AAPL")

    assert len(result) == 1
    assert result[0]["title"] == "Healthy article"


def test_manager_normalizes_article_fields():
    source = SpySource(
        [
            {
                "title": "  Example title  ",
                "source": "  Example source ",
                "summary": "  Example summary ",
                "url": "  https://example.com/article ",
                "sentiment": "POSITIVE",
                "published_at": " 20260914100000 ",
            }
        ]
    )

    manager = NewsSourceManager(
        sources={"alpha_vantage": source}
    )

    result = manager.latest("AAPL")

    assert result == [
        {
            "title": "Example title",
            "source": "Example source",
            "summary": "Example summary",
            "url": "https://example.com/article",
            "sentiment": "positive",
            "published_at": "20260914100000",
        }
    ]


def test_market_research_normalizes_sentiment_like_symbol_news(monkeypatch):
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "test-key")

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "feed": [
                    {
                        "title": "Markets react to new catalyst",
                        "source": "Example News",
                        "summary": "Broad market catalyst.",
                        "url": "https://example.com/market",
                        "overall_sentiment_label": "Somewhat-Bullish",
                        "time_published": "20260914100000",
                    }
                ]
            }

    monkeypatch.setattr(
        "atlas.news.alpha_vantage.requests.get",
        lambda *args, **kwargs: Response(),
    )

    result = AlphaVantageNewsAdapter().market_news(limit=10)

    assert result[0]["sentiment"] == "positive"

def test_alpha_vantage_market_news_preserves_related_tickers(monkeypatch):
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "test-key")

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "feed": [
                    {
                        "title": "Chip demand accelerates",
                        "source": "Example News",
                        "summary": "Semiconductor shares react.",
                        "url": "https://example.com/chips",
                        "overall_sentiment_label": "Bullish",
                        "time_published": "20260928100000",
                        "ticker_sentiment": [
                            {
                                "ticker": "AMD",
                                "relevance_score": "0.91",
                                "ticker_sentiment_score": "0.42",
                                "ticker_sentiment_label": "Bullish",
                            },
                            {
                                "ticker": "NVDA",
                                "relevance_score": "0.84",
                                "ticker_sentiment_score": "0.31",
                                "ticker_sentiment_label": "Somewhat-Bullish",
                            },
                        ],
                    }
                ]
            }

    monkeypatch.setattr(
        "atlas.news.alpha_vantage.requests.get",
        lambda *args, **kwargs: Response(),
    )

    result = AlphaVantageNewsAdapter().market_news(limit=10)

    assert result[0]["related_tickers"] == [
        {
            "symbol": "AMD",
            "relevance_score": 0.91,
            "sentiment_score": 0.42,
            "sentiment": "positive",
        },
        {
            "symbol": "NVDA",
            "relevance_score": 0.84,
            "sentiment_score": 0.31,
            "sentiment": "positive",
        },
    ]

def test_market_research_preserves_related_tickers_through_manager():
    class MarketNewsAdapter:
        def market_news(self, limit=50):
            return [
                {
                    "title": "Chip demand accelerates",
                    "source": "Example News",
                    "summary": "Semiconductor shares react.",
                    "url": "https://example.com/chips",
                    "sentiment": "positive",
                    "published_at": "20260928100000",
                    "related_tickers": [
                        {
                            "symbol": "AMD",
                            "relevance_score": 0.91,
                            "sentiment_score": 0.42,
                            "sentiment": "positive",
                        }
                    ],
                }
            ]

    class MarketNewsSource:
        adapter = MarketNewsAdapter()

    manager = NewsSourceManager(
        sources={"alpha_vantage": MarketNewsSource()}
    )

    result = manager.market_research(limit=10)

    assert result[0]["related_tickers"] == [
        {
            "symbol": "AMD",
            "relevance_score": 0.91,
            "sentiment_score": 0.42,
            "sentiment": "positive",
        }
    ]

