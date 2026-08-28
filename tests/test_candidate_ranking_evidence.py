from atlas.market.candidate_ranking_evidence import (
    CandidateRankingEvidence,
)


def test_candidate_ranking_evidence_contains_scores():
    evidence = CandidateRankingEvidence(
        symbol="BTC-USD",
        base_score=86.25,
        regime_fit=80.0,
        final_score=85.0,
    )

    assert evidence.symbol == "BTC-USD"
    assert evidence.base_score == 86.25
    assert evidence.regime_fit == 80.0
    assert evidence.final_score == 85.0


def test_candidate_ranking_evidence_contains_regime_context():
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

    assert evidence.regime == "LOW_VOLATILITY"
    assert evidence.strategy == "Momentum"
    assert evidence.regime_confidence == 80.0
    assert evidence.independent_run_count == 8
    assert evidence.robust_winner is True


def test_candidate_ranking_evidence_reasoning_is_explainable():
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

    assert evidence.reasoning == [
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


def test_candidate_ranking_evidence_without_regime_is_still_valid():
    evidence = CandidateRankingEvidence(
        symbol="ETH-USD",
        base_score=70.0,
        regime_fit=50.0,
        final_score=66.0,
    )

    assert evidence.reasoning == [
        "Base ranking score: 70.0000.",
        "Regime fit score: 50.0000.",
        "Final ranking score: 66.0000.",
    ]
