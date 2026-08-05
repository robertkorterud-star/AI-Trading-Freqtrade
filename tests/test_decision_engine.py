from atlas.agents.news_analyst import NewsAnalyst
from atlas.decision.engine import DecisionEngine
from atlas.models.action import Action


def test_decision_engine_returns_buy():

    analyst = NewsAnalyst()

    results = [
        analyst.analyze("BTC")
    ]

    engine = DecisionEngine()

    decision = engine.evaluate(results)

    assert decision.action == Action.BUY

    assert decision.evidence == 88.0

    assert decision.confidence == 91.0