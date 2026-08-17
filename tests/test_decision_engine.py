from atlas.agents.news_analyst import NewsAnalyst
from atlas.decision.engine import DecisionEngine
from atlas.models.action import Action


class FakeAIAdapter:

    def analyze_news(self, symbol, articles):
        return {
            "symbol": symbol,
            "relevance": 95,
            "sentiment": "POSITIVE",
            "impact": "HIGH",
            "time_horizon": "SHORT",
            "action": "BUY",
            "confidence": 95,
            "reason": "Strong positive evidence.",
        }


def test_decision_engine_returns_buy(monkeypatch):

    import atlas.adapters.ai

    monkeypatch.setattr(
        atlas.adapters.ai,
        "AIAdapter",
        FakeAIAdapter,
    )

    analyst = NewsAnalyst()

    articles = [
        {
            "title": "Strong positive market news",
            "summary": "Excellent developments.",
            "source": "Test News",
        }
    ]

    results = [
        analyst.analyze_news(
            "BTC",
            articles,
        )
    ]

    engine = DecisionEngine()

    decision = engine.evaluate(
        results
    )

    assert decision.action == Action.BUY
