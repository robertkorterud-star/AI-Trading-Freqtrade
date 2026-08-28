from atlas.market.candidate_ranking_evidence import (
    CandidateRankingEvidence,
)
from atlas.market.candidate_selection_report import (
    CandidateSelectionReport,
)


def test_candidate_selection_report_contains_selected_candidate():
    evidence = CandidateRankingEvidence(
        symbol="BTC-USD",
        base_score=86.25,
        regime_fit=80.0,
        final_score=85.0,
    )

    report = CandidateSelectionReport(
        symbol="BTC-USD",
        action="BUY",
        ranking_evidence=evidence,
    )

    assert report.symbol == "BTC-USD"
    assert report.action == "BUY"
    assert report.ranking_evidence is evidence


def test_candidate_selection_report_is_explainable():
    evidence = CandidateRankingEvidence(
        symbol="BTC-USD",
        base_score=86.25,
        regime_fit=80.0,
        final_score=85.0,
        regime="LOW_VOLATILITY",
        strategy="Momentum",
        regime_confidence=80.0,
        independent_run_count=8,
        robust_winner=True,
    )

    report = CandidateSelectionReport(
        symbol="BTC-USD",
        action="BUY",
        ranking_evidence=evidence,
    )

    assert report.reasoning == [
        "Selected candidate: BTC-USD.",
        "Action: BUY.",
        "Base ranking score: 86.2500.",
        "Regime fit score: 80.0000.",
        "Final ranking score: 85.0000.",
        "Market regime: LOW_VOLATILITY.",
        "Strategy-memory recommendation: Momentum.",
        "Regime-memory confidence: 80.0/100.",
        "Independent regime-memory runs: 8.",
        "Regime-memory recommendation is a robust "
        "historical winner.",
    ]


def test_candidate_selection_report_without_regime_is_valid():
    evidence = CandidateRankingEvidence(
        symbol="ETH-USD",
        base_score=70.0,
        regime_fit=50.0,
        final_score=66.0,
    )

    report = CandidateSelectionReport(
        symbol="ETH-USD",
        action="BUY",
        ranking_evidence=evidence,
    )

    assert report.reasoning == [
        "Selected candidate: ETH-USD.",
        "Action: BUY.",
        "Base ranking score: 70.0000.",
        "Regime fit score: 50.0000.",
        "Final ranking score: 66.0000.",
    ]


def test_candidate_selection_report_to_dict_is_machine_readable():
    evidence = CandidateRankingEvidence(
        symbol="BTC-USD",
        base_score=86.25,
        regime_fit=80.0,
        final_score=85.0,
        regime="LOW_VOLATILITY",
        strategy="Momentum",
        regime_confidence=80.0,
        independent_run_count=8,
        robust_winner=True,
    )

    report = CandidateSelectionReport(
        symbol="BTC-USD",
        action="BUY",
        ranking_evidence=evidence,
    )

    assert report.to_dict() == {
        "symbol": "BTC-USD",
        "action": "BUY",
        "ranking_evidence": {
            "symbol": "BTC-USD",
            "base_score": 86.25,
            "regime_fit": 80.0,
            "final_score": 85.0,
            "regime": "LOW_VOLATILITY",
            "strategy": "Momentum",
            "regime_confidence": 80.0,
            "independent_run_count": 8,
            "robust_winner": True,
        },
    }


def test_candidate_selection_report_to_dict_preserves_missing_regime():
    evidence = CandidateRankingEvidence(
        symbol="ETH-USD",
        base_score=70.0,
        regime_fit=50.0,
        final_score=66.0,
    )

    report = CandidateSelectionReport(
        symbol="ETH-USD",
        action="BUY",
        ranking_evidence=evidence,
    )

    result = report.to_dict()

    assert result["symbol"] == "ETH-USD"
    assert result["action"] == "BUY"
    assert result["ranking_evidence"]["regime"] is None
    assert result["ranking_evidence"]["strategy"] is None
    assert result["ranking_evidence"]["independent_run_count"] == 0
    assert result["ranking_evidence"]["robust_winner"] is False
