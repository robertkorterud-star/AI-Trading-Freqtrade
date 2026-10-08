from datetime import datetime, timezone

import pytest

from atlas.agents.news_analyst import NewsAnalyst
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult


@pytest.fixture
def observed_articles(monkeypatch):
    observed = []

    def fake_analyze_news(self, symbol, articles):
        observed.extend(articles)
        return AnalysisResult(
            analyst=self.name,
            symbol=symbol,
            action=Action.HOLD,
            confidence=0.0,
            evidence=60.0,
            reasoning=["Historical news test"],
            metadata={"news_items": self._serialize_articles(articles)},
        )

    monkeypatch.setattr(NewsAnalyst, "analyze_news", fake_analyze_news)
    return observed


def test_historical_news_excludes_future_and_unknown_articles(observed_articles):
    articles = [
        {"title": "Earlier", "published_at": "2026-09-14T12:00:00Z"},
        {"title": "Exactly now", "published_at": "2026-09-14T13:00:00Z"},
        {"title": "Future", "published_at": "2026-09-14T14:00:00Z"},
        {"title": "Unknown"},
    ]
    result = NewsAnalyst().analyze_with_news(
        "AAPL", articles, as_of=datetime(2026, 9, 14, 13, tzinfo=timezone.utc)
    )
    assert [a["title"] for a in observed_articles] == ["Earlier", "Exactly now"]
    assert [a["title"] for a in result.metadata["news_items"]] == ["Earlier", "Exactly now"]


def test_historical_news_accepts_supported_formats_and_rejects_invalid(observed_articles):
    articles = [
        {"title": "Invalid", "published_at": "not-a-date"},
        {"title": "Alpha Vantage", "published_at": "20260914120000"},
        {"title": "Finnhub", "published_at": 1789387200},
        {"title": "Naive", "published_at": "2026-09-14T12:00:00"},
        {"title": "Offset", "published_at": "2026-09-14T15:00:00+02:00"},
    ]
    NewsAnalyst().analyze_with_news(
        "AAPL", articles, as_of=datetime(2026, 9, 14, 13, tzinfo=timezone.utc)
    )
    assert [a["title"] for a in observed_articles] == ["Alpha Vantage", "Finnhub", "Offset"]


def test_historical_news_requires_aware_cutoff():
    with pytest.raises(ValueError, match="timezone-aware"):
        NewsAnalyst().analyze_with_news("AAPL", [], as_of=datetime(2026, 9, 14, 13))
