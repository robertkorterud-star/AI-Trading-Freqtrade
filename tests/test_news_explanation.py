from atlas.models.news_explanation import NewsExplanation


def test_news_explanation_defaults_and_values():

    explanation = NewsExplanation(
        symbol="BTC-USD",
        sentiment="POSITIVE",
        relevance=90.0,
        impact="HIGH",
        time_horizon="SHORT",
        action="BUY",
        confidence=92.0,
        reason="Strong positive market evidence.",
    )

    assert explanation.symbol == "BTC-USD"
    assert explanation.sentiment == "POSITIVE"
    assert explanation.relevance == 90.0
    assert explanation.impact == "HIGH"
    assert explanation.time_horizon == "SHORT"
    assert explanation.action == "BUY"
    assert explanation.confidence == 92.0
    assert explanation.reason == "Strong positive market evidence."


def test_news_explanation_supports_negative_signal():

    explanation = NewsExplanation(
        symbol="BTC-USD",
        sentiment="NEGATIVE",
        relevance=85.0,
        impact="HIGH",
        time_horizon="SHORT",
        action="SELL",
        confidence=84.0,
        reason="Strong negative market evidence.",
    )

    assert explanation.sentiment == "NEGATIVE"
    assert explanation.action == "SELL"
    assert explanation.confidence == 84.0
