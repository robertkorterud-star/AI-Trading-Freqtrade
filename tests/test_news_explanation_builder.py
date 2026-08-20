from atlas.news.explanation import explain_news
from atlas.models.news_explanation import NewsExplanation


def test_explain_news_builds_structured_explanation():

    analysis = {
        "symbol": "BTC-USD",
        "relevance": 90,
        "sentiment": "POSITIVE",
        "impact": "HIGH",
        "time_horizon": "SHORT",
        "action": "BUY",
        "confidence": 92,
        "reason": "Strong positive market evidence.",
    }

    explanation = explain_news(analysis)

    assert isinstance(
        explanation,
        NewsExplanation,
    )

    assert explanation.symbol == "BTC-USD"
    assert explanation.sentiment == "POSITIVE"
    assert explanation.relevance == 90.0
    assert explanation.impact == "HIGH"
    assert explanation.time_horizon == "SHORT"
    assert explanation.action == "BUY"
    assert explanation.confidence == 92.0
    assert explanation.reason == (
        "Strong positive market evidence."
    )


def test_explain_news_handles_missing_fields():

    explanation = explain_news(
        {
            "symbol": "ETH-USD",
        }
    )

    assert explanation.symbol == "ETH-USD"
    assert explanation.sentiment == "UNKNOWN"
    assert explanation.relevance == 0.0
    assert explanation.impact == "UNKNOWN"
    assert explanation.time_horizon == "UNKNOWN"
    assert explanation.action == "HOLD"
    assert explanation.confidence == 0.0
    assert explanation.reason == ""
