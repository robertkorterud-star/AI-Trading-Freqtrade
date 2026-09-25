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


def test_candidate_selection_report_selection_snapshot():
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

    snapshot = report.selection_snapshot

    assert snapshot["symbol"] == "BTC-USD"
    assert snapshot["action"] == "BUY"

    assert (
        snapshot["ranking_evidence"]["base_score"]
        == 86.25
    )

    assert (
        snapshot["ranking_evidence"]["regime_fit"]
        == 80.0
    )

    assert (
        snapshot["ranking_evidence"]["final_score"]
        == 85.0
    )

    assert (
        snapshot["ranking_evidence"]["regime"]
        == "LOW_VOLATILITY"
    )

    assert (
        snapshot["ranking_evidence"]["strategy"]
        == "Momentum"
    )

    assert snapshot["reasoning"] == (
        report.reasoning
    )




def test_candidate_selection_report_selection_snapshot_has_stable_contract():
    from atlas.market.candidate_selection_report import (
        CandidateSelectionReport,
    )
    from atlas.market.candidate_ranking_evidence import (
        CandidateRankingEvidence,
    )

    evidence = CandidateRankingEvidence(
        symbol="BTC-USD",
        base_score=90.0,
        regime_fit=85.0,
        final_score=88.5,
        regime="TREND",
        strategy="MOMENTUM",
        regime_confidence=92.0,
        independent_run_count=12,
        robust_winner=True,
    )

    report = CandidateSelectionReport(
        symbol="BTC-USD",
        action="BUY",
        ranking_evidence=evidence,
    )

    snapshot = report.selection_snapshot

    assert set(snapshot) == {
        "symbol",
        "action",
        "ranking_evidence",
        "reasoning",
    }

    assert snapshot["symbol"] == "BTC-USD"
    assert snapshot["action"] == "BUY"

    assert set(snapshot["ranking_evidence"]) == {
        "symbol",
        "base_score",
        "regime_fit",
        "final_score",
        "regime",
        "strategy",
        "regime_confidence",
        "independent_run_count",
        "robust_winner",
    }

    assert snapshot["ranking_evidence"]["symbol"] == "BTC-USD"
    assert snapshot["ranking_evidence"]["base_score"] == 90.0
    assert snapshot["ranking_evidence"]["regime_fit"] == 85.0
    assert snapshot["ranking_evidence"]["final_score"] == 88.5
    assert snapshot["ranking_evidence"]["regime"] == "TREND"
    assert snapshot["ranking_evidence"]["strategy"] == "MOMENTUM"
    assert snapshot["ranking_evidence"]["regime_confidence"] == 92.0
    assert snapshot["ranking_evidence"]["independent_run_count"] == 12
    assert snapshot["ranking_evidence"]["robust_winner"] is True

    assert snapshot["reasoning"] == report.reasoning

def test_candidate_selection_report_selection_snapshot_is_independent():
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

    snapshot = report.selection_snapshot

    snapshot["reasoning"].append("extra")

    assert "extra" not in report.reasoning


def test_candidate_selection_report_preserves_cost_adjusted_return_evidence():
    evidence = CandidateRankingEvidence(
        symbol="NVDA",
        base_score=88.0,
        regime_fit=75.0,
        final_score=85.4,
        expected_return=0.02,
        net_expected_return=0.0176,
        risk_adjusted_net_return=0.01408,
    )

    report = CandidateSelectionReport(
        symbol="NVDA",
        action="BUY",
        ranking_evidence=evidence,
    )

    ranking = report.to_dict()["ranking_evidence"]

    assert ranking["expected_return"] == 0.02
    assert ranking["net_expected_return"] == 0.0176
    assert ranking["risk_adjusted_net_return"] == 0.01408
    assert any(
        "Expected net return after trading costs" in line
        for line in report.reasoning
    )
