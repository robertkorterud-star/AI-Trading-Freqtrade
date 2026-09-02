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
    expected_return=0.0,
):
    return DecisionResult(
        symbol=symbol,
        action=action,
        confidence=confidence,
        evidence=evidence,
        robustness=robustness,
        decision_margin=decision_margin,
        expected_return=expected_return,
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


def test_regime_memory_can_change_ranking_without_changing_actions():
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.trading.strategy_memory_regime_decision_adapter import (
        StrategyMemoryRegimeDecision,
    )

    strong_base = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=90.0,
        evidence=90.0,
        robustness=90.0,
        decision_margin=30.0,
    )

    weaker_base = DecisionResult(
        symbol="ETH-USD",
        action=Action.BUY,
        confidence=88.0,
        evidence=88.0,
        robustness=88.0,
        decision_margin=25.0,
    )

    regime_decisions = {
        "BTC-USD": StrategyMemoryRegimeDecision(
            symbol="BTC-USD",
            regime="LOW_VOLATILITY",
            strategy=None,
            action=Action.HOLD,
            confidence=0.0,
            independent_run_count=0,
            robust_winner=False,
        ),
        "ETH-USD": StrategyMemoryRegimeDecision(
            symbol="ETH-USD",
            regime="LOW_VOLATILITY",
            strategy="Momentum",
            action=Action.HOLD,
            confidence=100.0,
            independent_run_count=12,
            robust_winner=True,
        ),
    }

    ranked = CandidateDecisionRanker().rank(
        [strong_base, weaker_base],
        regime_decisions=regime_decisions,
    )

    assert [decision.symbol for decision in ranked] == [
        "ETH-USD",
        "BTC-USD",
    ]

    # Regime-memory influences ranking only.
    assert strong_base.action == Action.BUY
    assert weaker_base.action == Action.BUY

    # The regime representation itself remains non-directional.
    assert (
        regime_decisions["ETH-USD"].action
        == Action.HOLD
    )


def test_ranker_prefers_higher_risk_adjusted_net_return():
    decisions = [
        make_decision(
            "LOW-RETURN",
            Action.BUY,
            95.0,
            95.0,
            95.0,
            40.0,
            expected_return=0.0030,
        ),
        make_decision(
            "HIGH-RETURN",
            Action.BUY,
            80.0,
            80.0,
            80.0,
            20.0,
            expected_return=0.0200,
        ),
    ]

    ranked = CandidateDecisionRanker().rank(decisions)

    assert [decision.symbol for decision in ranked] == [
        "HIGH-RETURN",
        "LOW-RETURN",
    ]


def test_ranker_evidence_exposes_cost_adjusted_return():
    decision = make_decision(
        "BTC-USD",
        Action.BUY,
        90.0,
        90.0,
        80.0,
        25.0,
        expected_return=0.0100,
    )

    evidence = CandidateDecisionRanker().rank_with_evidence(
        [decision]
    )[0]

    assert evidence.expected_return == 0.0100
    assert evidence.net_expected_return == 0.0076
    assert evidence.risk_adjusted_net_return == 0.00608
    assert any(
        "Expected net return after trading costs" in line
        for line in evidence.reasoning
    )
