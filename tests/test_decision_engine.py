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


def test_decision_engine_includes_agent_weights():

    from atlas.models.analysis_result import AnalysisResult

    class FakeWeightEngine:

        def calculate(self):
            return {
                "Technical Analyst": 0.60,
                "News Analyst": 0.40,
            }

    result = AnalysisResult(
        symbol="BTC-USD",
        analyst="Technical Analyst",
        action=Action.BUY,
        confidence=90.0,
        evidence=90.0,
        reasoning=["Strong technical evidence."],
    )

    engine = DecisionEngine()
    engine.agent_weight_engine = FakeWeightEngine()

    decision = engine.evaluate(
        [result]
    )

    assert decision.agent_weights == {
        "Technical Analyst": 0.60,
        "News Analyst": 0.40,
    }


def test_decision_engine_includes_agent_weights():

    from atlas.models.analysis_result import AnalysisResult

    class FakeWeightEngine:

        def calculate(self):
            return {
                "Technical Analyst": 0.60,
                "News Analyst": 0.40,
            }

    result = AnalysisResult(
        symbol="BTC-USD",
        analyst="Technical Analyst",
        action=Action.BUY,
        confidence=90.0,
        evidence=90.0,
        reasoning=["Strong technical evidence."],
    )

    engine = DecisionEngine()
    engine.agent_weight_engine = FakeWeightEngine()

    decision = engine.evaluate(
        [result]
    )

    assert decision.agent_weights == {
        "Technical Analyst": 0.60,
        "News Analyst": 0.40,
    }
