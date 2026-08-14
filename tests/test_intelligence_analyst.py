from unittest.mock import patch

from atlas.agents.intelligence_analyst import IntelligenceAnalyst
from atlas.models.action import Action


def test_intelligence_analyst_identifies_positive_research():
    with patch(
        "atlas.agents.intelligence_analyst.IntelligenceSourceAdapter.get",
        return_value=[
            {
                "source": "YouTube",
                "title": "NVIDIA outlook remains strong",
                "summary": "Strong demand for AI infrastructure.",
                "sentiment": "positive",
            },
            {
                "source": "Reuters",
                "title": "NVIDIA demand continues",
                "summary": "Data center demand remains strong.",
                "sentiment": "positive",
            },
            {
                "source": "Finnhub",
                "title": "Analysts discuss NVIDIA growth",
                "summary": "Growth expectations remain positive.",
                "sentiment": "positive",
            },
        ],
    ):
        result = IntelligenceAnalyst().analyze("NVDA")

    assert result.analyst == "Intelligence Analyst"
    assert result.symbol == "NVDA"
    assert result.action == Action.BUY
    assert result.confidence == 85.0
    assert result.evidence == 95.0
    assert len(result.reasoning) >= 3


def test_intelligence_analyst_identifies_negative_research():
    with patch(
        "atlas.agents.intelligence_analyst.IntelligenceSourceAdapter.get",
        return_value=[
            {
                "source": "YouTube",
                "title": "NVIDIA risks increase",
                "summary": "Competition and valuation concerns.",
                "sentiment": "negative",
            },
            {
                "source": "Reuters",
                "title": "NVIDIA faces headwinds",
                "summary": "Demand concerns emerge.",
                "sentiment": "negative",
            },
            {
                "source": "Finnhub",
                "title": "Analysts lower expectations",
                "summary": "Growth outlook weakens.",
                "sentiment": "negative",
            },
        ],
    ):
        result = IntelligenceAnalyst().analyze("NVDA")

    assert result.analyst == "Intelligence Analyst"
    assert result.symbol == "NVDA"
    assert result.action == Action.SELL
    assert result.confidence == 60.0


def test_intelligence_analyst_handles_no_sources():
    with patch(
        "atlas.agents.intelligence_analyst.IntelligenceSourceAdapter.get",
        return_value=[],
    ):
        result = IntelligenceAnalyst().analyze("NVDA")

    assert result.analyst == "Intelligence Analyst"
    assert result.symbol == "NVDA"
    assert result.action == Action.HOLD
    assert result.confidence == 50.0
    assert result.evidence == 50.0
