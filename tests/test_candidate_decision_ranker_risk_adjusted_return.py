from atlas.market.candidate_decision_ranker import CandidateDecisionRanker
from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult


def make_candidate(
    symbol: str,
    expected_return: float,
    robustness: float,
) -> DecisionResult:
    return DecisionResult(
        action=Action.BUY,
        symbol=symbol,
        confidence=80.0,
        evidence=80.0,
        robustness=robustness,
        decision_margin=20.0,
        expected_return=expected_return,
    )


def test_ranker_prefers_better_risk_adjusted_net_return():
    ranker = CandidateDecisionRanker()

    high_gross_low_robustness = make_candidate(
        "HIGH-GROSS",
        expected_return=0.020,
        robustness=40.0,
    )

    lower_gross_high_robustness = make_candidate(
        "HIGH-RISK-ADJUSTED",
        expected_return=0.012,
        robustness=90.0,
    )

    ranked = ranker.rank(
        [
            high_gross_low_robustness,
            lower_gross_high_robustness,
        ]
    )

    assert ranked[0].symbol == "HIGH-RISK-ADJUSTED"

    evidence = ranker.rank_with_evidence(
        [
            high_gross_low_robustness,
            lower_gross_high_robustness,
        ]
    )[0]

    assert evidence.expected_return == 0.012
    assert evidence.net_expected_return > 0.0
    assert evidence.risk_adjusted_net_return > 0.0
