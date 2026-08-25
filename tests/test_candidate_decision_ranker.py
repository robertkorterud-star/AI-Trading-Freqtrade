from atlas.market.candidate_decision_ranker import (
    CandidateDecisionRanker,
)
from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult


def make_decision(
    symbol,
    action,
    confidence,
    evidence,
    robustness,
    decision_margin,
):
    return DecisionResult(
        symbol=symbol,
        action=action,
        confidence=confidence,
        evidence=evidence,
        robustness=robustness,
        decision_margin=decision_margin,
    )


def test_ranker_prefers_strong_buy():

    decisions = [
        make_decision(
            "AAPL",
            Action.BUY,
            80.0,
            80.0,
            60.0,
            15.0,
        ),
        make_decision(
            "NVDA",
            Action.BUY,
            90.0,
            92.0,
            85.0,
            30.0,
        ),
    ]

    ranked = CandidateDecisionRanker().rank(
        decisions
    )

    assert [
        decision.symbol
        for decision in ranked
    ] == [
        "NVDA",
        "AAPL",
    ]


def test_ranker_prefers_buy_over_hold():

    decisions = [
        make_decision(
            "BTC-USD",
            Action.HOLD,
            95.0,
            90.0,
            90.0,
            40.0,
        ),
        make_decision(
            "NVDA",
            Action.BUY,
            75.0,
            80.0,
            65.0,
            20.0,
        ),
    ]

    ranked = CandidateDecisionRanker().rank(
        decisions
    )

    assert ranked[0].symbol == "NVDA"


def test_ranker_can_return_only_investable_actions():

    decisions = [
        make_decision(
            "BTC-USD",
            Action.HOLD,
            90.0,
            90.0,
            90.0,
            40.0,
        ),
        make_decision(
            "NVDA",
            Action.BUY,
            80.0,
            85.0,
            75.0,
            25.0,
        ),
        make_decision(
            "AAPL",
            Action.SELL,
            85.0,
            88.0,
            80.0,
            30.0,
        ),
    ]

    ranked = CandidateDecisionRanker().rank(
        decisions,
        investable_only=True,
    )

    assert [
        decision.symbol
        for decision in ranked
    ] == [
        "NVDA",
        "AAPL",
    ]


def test_ranker_does_not_modify_decisions():

    decision = make_decision(
        "NVDA",
        Action.BUY,
        90.0,
        90.0,
        80.0,
        25.0,
    )

    ranked = CandidateDecisionRanker().rank(
        [decision]
    )

    assert ranked[0] is decision
