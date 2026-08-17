from atlas.agents.news_analyst import NewsAnalyst
from atlas.models.action import Action


class FakeAIAdapter:

    def analyze_news(self, symbol, articles):
        return {
            "symbol": symbol,
            "relevance": 90,
            "sentiment": "POSITIVE",
            "impact": "HIGH",
            "time_horizon": "SHORT",
            "action": "BUY",
            "confidence": 92,
            "reason": "Strong positive market evidence.",
        }


def test_news_analyst_returns_analysis_result(monkeypatch):

    analyst = NewsAnalyst()

    monkeypatch.setattr(
        "atlas.agents.news_analyst.AIAdapter",
        FakeAIAdapter,
        raising=False,
    )

    # AIAdapter is imported inside analyze_news(), so patch
    # the module where it is actually imported.
    import atlas.adapters.ai

    monkeypatch.setattr(
        atlas.adapters.ai,
        "AIAdapter",
        FakeAIAdapter,
    )

    articles = [
        {
            "title": "Strong positive news",
            "summary": "Excellent market development.",
            "source": "Test News",
        }
    ]

    result = analyst.analyze_news(
        "BTC",
        articles,
    )

    assert result.symbol == "BTC"
    assert result.analyst == "News Analyst"
    assert result.action == Action.BUY
    assert result.confidence == 92
    assert result.evidence == 95
    assert result.reasoning
