"""
News Explanation Builder

Converts structured AI news analysis into a
human-readable NewsExplanation.
"""

from atlas.models.news_explanation import NewsExplanation


def explain_news(
    analysis: dict,
) -> NewsExplanation:
    """Build a structured explanation from AI news analysis."""

    return NewsExplanation(
        symbol=str(
            analysis.get("symbol", "")
        ),
        sentiment=str(
            analysis.get("sentiment", "UNKNOWN")
        ),
        relevance=float(
            analysis.get("relevance", 0.0)
        ),
        impact=str(
            analysis.get("impact", "UNKNOWN")
        ),
        time_horizon=str(
            analysis.get("time_horizon", "UNKNOWN")
        ),
        action=str(
            analysis.get("action", "HOLD")
        ),
        confidence=float(
            analysis.get("confidence", 0.0)
        ),
        reason=str(
            analysis.get("reason", "")
        ),
    )
