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


def test_realistic_expected_returns_remain_distinguishable_before_saturation():
    ranker = CandidateDecisionRanker()

    gross_returns = [0.003, 0.005, 0.010, 0.015]
    scores = [
        ranker.build_evidence_with_cost_model(
            make_decision(expected_return)
        ).final_score
        for expected_return in gross_returns
    ]

    assert scores == sorted(scores)
    assert len(set(scores)) == len(scores)
    assert scores[-1] < 100.0


def test_return_score_calibration_at_common_net_return_levels():
    ranker = CandidateDecisionRanker()

    # With the default 0.24% round-trip cost and full robustness,
    # these gross returns produce the following risk-adjusted net returns.
    cases = [
        (0.003, 0.0006, 53.0),
        (0.005, 0.0026, 63.0),
        (0.010, 0.0076, 88.0),
        (0.015, 0.0126, 100.0),
    ]

    for gross_return, expected_net, expected_score in cases:
        evidence = ranker.build_evidence_with_cost_model(
            make_decision(gross_return)
        )

        assert evidence.risk_adjusted_net_return == pytest.approx(expected_net)
        assert ranker._net_return_score(evidence.risk_adjusted_net_return) == pytest.approx(
            expected_score
        )


def test_costs_create_a_meaningful_return_threshold():
    ranker = CandidateDecisionRanker()

    below_cost = ranker.build_evidence_with_cost_model(make_decision(0.0023))
    at_cost = ranker.build_evidence_with_cost_model(make_decision(0.0024))
    above_cost = ranker.build_evidence_with_cost_model(make_decision(0.0030))

    assert below_cost.net_expected_return == pytest.approx(-0.0001)
    assert at_cost.net_expected_return == pytest.approx(0.0)
    assert above_cost.net_expected_return == pytest.approx(0.0006)

    assert below_cost.risk_adjusted_net_return < at_cost.risk_adjusted_net_return
    assert at_cost.risk_adjusted_net_return < above_cost.risk_adjusted_net_return
