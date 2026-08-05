from atlas.agents.news_analyst import NewsAnalyst
from atlas.models.action import Action


def test_news_analyst_returns_analysis_result():
    analyst = NewsAnalyst()

    result = analyst.analyze("BTC")

    assert result.symbol == "BTC"
    assert result.action == Action.BUY
    assert result.evidence == 88.0
    assert result.confidence == 91.0