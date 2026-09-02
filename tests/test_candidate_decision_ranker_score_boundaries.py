import pytest

from atlas.market.candidate_decision_ranker import CandidateDecisionRanker
from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult


def make_decision(expected_return, robustness=100.0):
    return DecisionResult(
        symbol="TEST",
        action=Action.BUY,
        confidence=80.0,
        evidence=80.0,
        robustness=robustness,
        decision_margin=20.0,
        expected_return=expected_return,
    )


def test_net_return_score_is_bounded_to_zero_to_hundred():
    ranker = CandidateDecisionRanker()

    assert ranker._net_return_score(-1.0) == 0.0
    assert ranker._net_return_score(0.0) == 50.0
    assert ranker._net_return_score(1.0) == 100.0


def test_net_return_score_is_monotonic_before_saturation():
    ranker = CandidateDecisionRanker()

    lower = ranker._net_return_score(0.001)
    middle = ranker._net_return_score(0.003)
    higher = ranker._net_return_score(0.005)

    assert 50.0 < lower < middle < higher < 100.0


def test_risk_adjusted_net_return_uses_clamped_robustness():
    ranker = CandidateDecisionRanker()

    negative_robustness = ranker.build_evidence_with_cost_model(
        make_decision(0.0100, robustness=-20.0)
    )
    excessive_robustness = ranker.build_evidence_with_cost_model(
        make_decision(0.0100, robustness=120.0)
    )

    assert negative_robustness.risk_adjusted_net_return == pytest.approx(0.0)
    assert excessive_robustness.risk_adjusted_net_return == pytest.approx(0.0076)


def test_large_positive_return_score_saturates_at_hundred():
    ranker = CandidateDecisionRanker()

    evidence = ranker.build_evidence_with_cost_model(
        make_decision(0.1000, robustness=100.0)
    )

    assert evidence.risk_adjusted_net_return == pytest.approx(0.0976)
    assert ranker._net_return_score(evidence.risk_adjusted_net_return) == 100.0
