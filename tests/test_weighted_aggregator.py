from atlas.decision.aggregator import EvidenceAggregator
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult


def result(
    analyst,
    evidence,
    confidence,
    action=Action.BUY,
):
    return AnalysisResult(
        analyst=analyst,
        symbol="NVDA",
        action=action,
        confidence=confidence,
        evidence=evidence,
        reasoning=[],
    )


def test_weighted_aggregator_uses_agent_weights():

    aggregator = EvidenceAggregator()

    results = [
        result(
            "Technical Analyst",
            evidence=100,
            confidence=100,
        ),
        result(
            "News Analyst",
            evidence=50,
            confidence=50,
        ),
        result(
            "Company Analyst",
            evidence=50,
            confidence=50,
        ),
    ]

    weights = {
        "Technical Analyst": 0.60,
        "News Analyst": 0.20,
        "Company Analyst": 0.20,
    }

    summary = aggregator.summarize(
        results,
        weights=weights,
    )

    assert summary["evidence"] == 80.0
    assert summary["confidence"] == 80.0


def test_weighted_aggregator_defaults_to_equal_weights():

    aggregator = EvidenceAggregator()

    results = [
        result(
            "Technical Analyst",
            evidence=100,
            confidence=100,
        ),
        result(
            "News Analyst",
            evidence=50,
            confidence=50,
        ),
    ]

    summary = aggregator.summarize(results)

    assert summary["evidence"] == 75.0
    assert summary["confidence"] == 75.0


def test_unknown_analyst_weight_does_not_break_aggregation():

    aggregator = EvidenceAggregator()

    results = [
        result(
            "Technical Analyst",
            evidence=100,
            confidence=100,
        ),
        result(
            "News Analyst",
            evidence=50,
            confidence=50,
        ),
    ]

    weights = {
        "Technical Analyst": 0.60,
    }

    summary = aggregator.summarize(
        results,
        weights=weights,
    )

    assert "evidence" in summary
    assert "confidence" in summary
