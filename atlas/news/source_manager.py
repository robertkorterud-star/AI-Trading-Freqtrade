"""Policy-driven, process-local collection of current news sources."""

from dataclasses import asdict, is_dataclass
import time

from atlas.adapters.direct_publisher_news import DirectPublisherNewsAdapter
from atlas.adapters.news import NewsAdapter
from atlas.adapters.youtube import YouTubeAdapter
from atlas.news.alpha_vantage import AlphaVantageNewsAdapter


class _FinnhubSource:
    """Keep the established NewsAdapter as the Finnhub source."""

    def fetch(self, symbol: str) -> list:
        try:
            return NewsAdapter().latest(symbol)
        except Exception:
            return []


class _AdapterSource:
    """Adapt existing search-style adapters to the manager source contract."""

    def __init__(self, adapter) -> None:
        self.adapter = adapter

    def fetch(self, symbol: str) -> list:
        return self.adapter.search(symbol)


class NewsSourceManager:
    """Collect current news under source-specific freshness policies.

    The cache is deliberately process-local. Historical analysis snapshots remain
    the sole record of the articles ultimately used by NewsAnalyst.
    """

    FRESHNESS_SECONDS = {
        "alpha_vantage": 10 * 60,
        "finnhub": 10 * 60,
        "publishers": 15 * 60,
        "youtube": 24 * 60 * 60,
    }

    def __init__(self, sources=None, clock=None) -> None:
        self.sources = sources or {
            "alpha_vantage": _AdapterSource(AlphaVantageNewsAdapter()),
            "finnhub": _FinnhubSource(),
            "publishers": _AdapterSource(DirectPublisherNewsAdapter()),
            "youtube": _AdapterSource(YouTubeAdapter()),
        }
        self._clock = clock or time.monotonic
        self._cache = {}

    @staticmethod
    def _normalize(article) -> dict:
        if isinstance(article, dict):
            data = dict(article)
        elif is_dataclass(article):
            data = asdict(article)
        else:
            data = {
                "title": getattr(article, "title", ""),
                "source": getattr(article, "source", ""),
                "summary": getattr(article, "summary", ""),
                "url": getattr(article, "url", ""),
                "sentiment": getattr(article, "sentiment", "neutral"),
                "published_at": getattr(article, "published_at", ""),
            }

        return {
            "title": str(data.get("title", "")).strip(),
            "source": str(data.get("source", "")).strip(),
            "summary": str(data.get("summary", "")).strip(),
            "url": str(data.get("url", "")).strip(),
            "sentiment": str(data.get("sentiment", "neutral")).lower(),
            "published_at": str(data.get("published_at", "")).strip(),
        }

    @staticmethod
    def _identity(article: dict) -> tuple:
        if article["url"]:
            return ("url", article["url"])
        return (
            "article",
            article["source"],
            article["title"],
            article["published_at"],
        )

    def _fetch_source(self, name: str, source, symbol: str) -> list:
        key = (name, symbol.upper().strip())
        now = self._clock()
        cached = self._cache.get(key)
        if cached is not None:
            fetched_at, articles = cached
            if now - fetched_at < self.FRESHNESS_SECONDS[name]:
                return list(articles)

        try:
            articles = source.fetch(symbol)
        except Exception:
            articles = []

        if not isinstance(articles, list):
            articles = []
        self._cache[key] = (now, list(articles))
        return articles

    def market_research(self, limit: int = 50) -> list[dict]:
        """Return cached broad-market research for candidate discovery."""

        name = "alpha_vantage"
        source = self.sources.get(name)

        if source is None:
            return []

        key = (name, "__MARKET__")
        now = self._clock()
        cached = self._cache.get(key)

        if cached is not None:
            fetched_at, articles = cached
            if now - fetched_at < self.FRESHNESS_SECONDS[name]:
                return list(articles)

        try:
            adapter = getattr(source, "adapter", None)

            if adapter is None or not hasattr(adapter, "market_news"):
                return []

            articles = adapter.market_news(limit=limit)
        except Exception:
            articles = []

        if not isinstance(articles, list):
            articles = []

        normalized_articles = []
        seen = set()

        for article in articles:
            normalized = self._normalize(article)

            if not normalized["title"]:
                continue

            identity = self._identity(normalized)

            if identity in seen:
                continue

            seen.add(identity)
            normalized_articles.append(normalized)

        self._cache[key] = (
            now,
            list(normalized_articles),
        )

        return normalized_articles

    def latest(self, symbol: str) -> list[dict]:
        """Return deduplicated articles in source-policy order."""

        articles = []
        seen = set()
        for name, source in self.sources.items():
            for article in self._fetch_source(name, source, symbol):
                normalized = self._normalize(article)
                if not normalized["title"]:
                    continue
                identity = self._identity(normalized)
                if identity in seen:
                    continue
                seen.add(identity)
                articles.append(normalized)
        return articles
