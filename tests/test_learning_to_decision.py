from atlas.decision.engine import DecisionEngine
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult
from atlas.trading.agent_performance_tracker import AgentPerformanceTracker
from atlas.trading.agent_weight_engine import AgentWeightEngine



def record_action_history(
    tracker,
    analyst,
    action,
    correct,
    wrong,
):
    for _ in range(correct):
        tracker.record(
            analyst,
            True,
            action,
        )

    for _ in range(wrong):
        tracker.record(
            analyst,
            False,
            action,
        )


def add_predictions(
    tracker,
    analyst,
    correct,
    count,
):
    for _ in range(count):
        tracker.record(
            analyst=analyst,
            correct=correct,
        )


def make_result(
    analyst,
    action,
    evidence=100.0,
    confidence=100.0,
):
    return AnalysisResult(
        symbol="BTC-USD",
        analyst=analyst,
        action=action,
        confidence=confidence,
        evidence=evidence,
        reasoning=[f"{analyst} signal"],
    )


def evaluate(
    technical_correct,
    technical_total=100,
    technical_action=Action.BUY,
    news_action=Action.SELL,
    company_action=Action.SELL,
):
    tracker = AgentPerformanceTracker()

    add_predictions(
        tracker,
        "Technical Analyst",
        True,
        technical_correct,
    )

    add_predictions(
        tracker,
        "Technical Analyst",
        False,
        technical_total - technical_correct,
    )

    add_predictions(
        tracker,
        "News Analyst",
        False,
        100,
    )

    add_predictions(
        tracker,
        "Company Analyst",
        False,
        100,
    )

    weight_engine = AgentWeightEngine(tracker)

    engine = DecisionEngine()
    engine.agent_weight_engine = weight_engine

    return engine.evaluate(
        [
            make_result(
                "Technical Analyst",
                technical_action,
            ),
            make_result(
                "News Analyst",
                news_action,
            ),
            make_result(
                "Company Analyst",
                company_action,
            ),
        ]
    )


def test_learning_override_requires_strong_margin():
    decision = evaluate(
        technical_correct=80,
    )

    assert decision.dominant_weight >= 0.60 * 100
    assert decision.decision_margin >= 20.0
    assert decision.action == Action.BUY
    assert decision.adaptive_override is True


def test_learning_override_activates_at_exact_margin_boundary():
    decision = evaluate(
        technical_correct=40,
    )

    assert decision.dominant_action == Action.BUY
    assert decision.dominant_weight == 60.0
    assert decision.decision_margin == 20.0
    assert decision.action == Action.BUY
    assert decision.adaptive_override is True


def test_learning_does_not_override_with_weak_evidence():
    tracker = AgentPerformanceTracker()

    add_predictions(
        tracker,
        "Technical Analyst",
        True,
        100,
    )

    add_predictions(
        tracker,
        "News Analyst",
        False,
        100,
    )

    add_predictions(
        tracker,
        "Company Analyst",
        False,
        100,
    )

    engine = DecisionEngine()
    engine.agent_weight_engine = AgentWeightEngine(
        tracker
    )

    decision = engine.evaluate(
        [
            make_result(
                "Technical Analyst",
                Action.BUY,
                evidence=50.0,
            ),
            make_result(
                "News Analyst",
                Action.SELL,
                evidence=50.0,
            ),
            make_result(
                "Company Analyst",
                Action.SELL,
                evidence=50.0,
            ),
        ]
    )

    assert decision.dominant_action == Action.BUY
    assert decision.dominant_weight == 60.0
    assert decision.action == Action.HOLD
    assert decision.adaptive_override is False


def test_learning_override_can_resolve_sell_conflict():
    decision = evaluate(
        technical_correct=80,
        technical_action=Action.SELL,
        news_action=Action.BUY,
        company_action=Action.BUY,
    )

    assert decision.dominant_action == Action.SELL
    assert decision.dominant_weight >= 60.0
    assert decision.decision_margin >= 20.0
    assert decision.action == Action.SELL
    assert decision.adaptive_override is True


def test_decision_engine_uses_action_specific_weights():

    tracker = AgentPerformanceTracker()

    # BUY performance:
    #
    # Technical Analyst: 90% BUY accuracy
    # Company Analyst:   50% BUY accuracy
    # News Analyst:      30% BUY accuracy

    record_action_history(
        tracker,
        "Technical Analyst",
        "BUY",
        18,
        2,
    )

    record_action_history(
        tracker,
        "Company Analyst",
        "BUY",
        10,
        10,
    )

    record_action_history(
        tracker,
        "News Analyst",
        "BUY",
        6,
        14,
    )

    # SELL performance:
    #
    # Technical Analyst: 30% SELL accuracy
    # Company Analyst:   50% SELL accuracy
    # News Analyst:      90% SELL accuracy

    record_action_history(
        tracker,
        "Technical Analyst",
        "SELL",
        6,
        14,
    )

    record_action_history(
        tracker,
        "Company Analyst",
        "SELL",
        10,
        10,
    )

    record_action_history(
        tracker,
        "News Analyst",
        "SELL",
        18,
        2,
    )

    weight_engine = AgentWeightEngine(
        tracker
    )

    buy_weights = weight_engine.calculate(
        action="BUY"
    )

    sell_weights = weight_engine.calculate(
        action="SELL"
    )

    assert buy_weights["Technical Analyst"] > (
        buy_weights["Company Analyst"]
    )

    assert buy_weights["Company Analyst"] > (
        buy_weights["News Analyst"]
    )

    assert sell_weights["News Analyst"] > (
        sell_weights["Company Analyst"]
    )

    assert sell_weights["Company Analyst"] > (
        sell_weights["Technical Analyst"]
    )

    assert buy_weights != sell_weights

    assert round(
        sum(buy_weights.values()),
        4,
    ) == 1.0

    assert round(
        sum(sell_weights.values()),
        4,
    ) == 1.0


def test_decision_engine_applies_buy_specific_weights():

    tracker = AgentPerformanceTracker()

    # Technical is highly accurate for BUY.
    record_action_history(
        tracker,
        "Technical Analyst",
        "BUY",
        18,
        2,
    )

    # Company is neutral.
    record_action_history(
        tracker,
        "Company Analyst",
        "BUY",
        10,
        10,
    )

    # News is weak for BUY.
    record_action_history(
        tracker,
        "News Analyst",
        "BUY",
        6,
        14,
    )

    weight_engine = AgentWeightEngine(
        tracker
    )

    engine = DecisionEngine()
    engine.agent_weight_engine = weight_engine

    decision = engine.evaluate(
        [
            make_result(
                "Technical Analyst",
                Action.BUY,
            ),
            make_result(
                "Company Analyst",
                Action.SELL,
            ),
            make_result(
                "News Analyst",
                Action.SELL,
            ),
        ]
    )

    expected_buy_weights = (
        weight_engine.calculate(action="BUY")
    )

    assert decision.agent_weights == (
        expected_buy_weights
    )

    assert (
        decision.agent_weights["Technical Analyst"]
        > decision.agent_weights["Company Analyst"]
    )

    assert (
        decision.agent_weights["Company Analyst"]
        > decision.agent_weights["News Analyst"]
    )


def test_decision_engine_reports_action_specific_weights_used():

    tracker = AgentPerformanceTracker()

    # BUY history:
    # Technical = 90%
    # Company = 50%
    # News = 30%

    record_action_history(
        tracker,
        "Technical Analyst",
        "BUY",
        18,
        2,
    )

    record_action_history(
        tracker,
        "Company Analyst",
        "BUY",
        10,
        10,
    )

    record_action_history(
        tracker,
        "News Analyst",
        "BUY",
        6,
        14,
    )

    engine = DecisionEngine()

    engine.agent_weight_engine = (
        AgentWeightEngine(tracker)
    )

    decision = engine.evaluate(
        [
            make_result(
                "Technical Analyst",
                Action.BUY,
            ),
            make_result(
                "Company Analyst",
                Action.SELL,
            ),
            make_result(
                "News Analyst",
                Action.SELL,
            ),
        ]
    )

    expected = (
        engine.agent_weight_engine.calculate(
            action="BUY",
        )
    )

    assert decision.agent_weights == expected


def test_learning_override_uses_action_specific_history():

    tracker = AgentPerformanceTracker()

    # Technical Analyst is strong on BUY.
    record_action_history(
        tracker,
        "Technical Analyst",
        "BUY",
        18,
        2,
    )

    # Technical Analyst is weak on SELL.
    record_action_history(
        tracker,
        "Technical Analyst",
        "SELL",
        6,
        14,
    )

    # Company Analyst is neutral.
    for action in ("BUY", "SELL"):
        for _ in range(10):
            tracker.record(
                "Company Analyst",
                True,
                action,
            )

        for _ in range(10):
            tracker.record(
                "Company Analyst",
                False,
                action,
            )

    # News Analyst is weak on BUY.
    record_action_history(
        tracker,
        "News Analyst",
        "BUY",
        6,
        14,
    )

    # News Analyst is strong on SELL.
    record_action_history(
        tracker,
        "News Analyst",
        "SELL",
        18,
        2,
    )

    weight_engine = AgentWeightEngine(
        tracker
    )

    buy_weights = weight_engine.calculate(
        action="BUY",
    )

    sell_weights = weight_engine.calculate(
        action="SELL",
    )

    assert buy_weights["Technical Analyst"] > (
        buy_weights["Company Analyst"]
    )

    assert sell_weights["News Analyst"] > (
        sell_weights["Company Analyst"]
    )

    assert buy_weights["Technical Analyst"] > (
        sell_weights["Technical Analyst"]
    )

    assert sell_weights["News Analyst"] > (
        buy_weights["News Analyst"]
    )


def test_decision_engine_uses_action_learning_for_override_only():

    tracker = AgentPerformanceTracker()

    # Technical is highly reliable for BUY.
    record_action_history(
        tracker,
        "Technical Analyst",
        "BUY",
        18,
        2,
    )

    # Technical is weak for SELL.
    record_action_history(
        tracker,
        "Technical Analyst",
        "SELL",
        6,
        14,
    )

    # Company remains neutral.
    for action in ("BUY", "SELL"):
        for _ in range(10):
            tracker.record(
                "Company Analyst",
                True,
                action,
            )

        for _ in range(10):
            tracker.record(
                "Company Analyst",
                False,
                action,
            )

    # News is weak for BUY.
    record_action_history(
        tracker,
        "News Analyst",
        "BUY",
        6,
        14,
    )

    # News is strong for SELL.
    record_action_history(
        tracker,
        "News Analyst",
        "SELL",
        18,
        2,
    )

    engine = DecisionEngine()
    engine.agent_weight_engine = AgentWeightEngine(
        tracker
    )

    decision = engine.evaluate(
        [
            make_result(
                "Technical Analyst",
                Action.BUY,
            ),
            make_result(
                "Company Analyst",
                Action.SELL,
            ),
            make_result(
                "News Analyst",
                Action.SELL,
            ),
        ]
    )

    # The decision must remain a BUY/SELL conflict unless
    # the existing adaptive override criteria are satisfied.
    assert decision.dominant_action in {
        Action.BUY,
        Action.SELL,
    }

    assert decision.agent_weights == (
        engine.agent_weight_engine.calculate()
    )


def test_action_specific_learning_identifies_strong_supporting_agent():

    tracker = AgentPerformanceTracker()

    # Technical Analyst: strong BUY history.
    record_action_history(
        tracker,
        "Technical Analyst",
        "BUY",
        18,
        2,
    )

    # Technical Analyst: weak SELL history.
    record_action_history(
        tracker,
        "Technical Analyst",
        "SELL",
        6,
        14,
    )

    # Company Analyst: neutral.
    for action in ("BUY", "SELL"):
        for _ in range(10):
            tracker.record(
                "Company Analyst",
                True,
                action,
            )

        for _ in range(10):
            tracker.record(
                "Company Analyst",
                False,
                action,
            )

    # News Analyst: weak BUY history.
    record_action_history(
        tracker,
        "News Analyst",
        "BUY",
        6,
        14,
    )

    # News Analyst: strong SELL history.
    record_action_history(
        tracker,
        "News Analyst",
        "SELL",
        18,
        2,
    )

    engine = AgentWeightEngine(tracker)

    buy_weights = engine.calculate(
        action="BUY",
    )

    sell_weights = engine.calculate(
        action="SELL",
    )

    # The learned action-specific weights identify
    # which analyst is strongest for each direction.
    assert max(
        buy_weights,
        key=buy_weights.get,
    ) == "Technical Analyst"

    assert max(
        sell_weights,
        key=sell_weights.get,
    ) == "News Analyst"


def test_decision_engine_finds_strongest_action_support():

    tracker = AgentPerformanceTracker()

    # Technical is strongest for BUY.
    record_action_history(
        tracker,
        "Technical Analyst",
        "BUY",
        18,
        2,
    )

    # Company is neutral.
    record_action_history(
        tracker,
        "Company Analyst",
        "BUY",
        10,
        10,
    )

    # News is weakest for BUY.
    record_action_history(
        tracker,
        "News Analyst",
        "BUY",
        6,
        14,
    )

    engine = DecisionEngine()
    engine.agent_weight_engine = AgentWeightEngine(
        tracker
    )

    support = engine._strongest_action_support(
        Action.BUY,
    )

    assert support is not None
    assert support["action"] == "BUY"
    assert support["analyst"] == "Technical Analyst"
    assert support["weight"] == 0.4063


def test_learning_override_requires_strong_action_specific_support():

    tracker = AgentPerformanceTracker()

    # Technical: strong BUY history.
    record_action_history(
        tracker,
        "Technical Analyst",
        "BUY",
        18,
        2,
    )

    # Company: neutral.
    record_action_history(
        tracker,
        "Company Analyst",
        "BUY",
        10,
        10,
    )

    # News: weak BUY history.
    record_action_history(
        tracker,
        "News Analyst",
        "BUY",
        6,
        14,
    )

    engine = DecisionEngine()
    engine.agent_weight_engine = AgentWeightEngine(
        tracker
    )

    support = engine._strongest_action_support(
        Action.BUY,
    )

    assert support["analyst"] == "Technical Analyst"
    assert support["weight"] >= 0.40


def test_decision_result_reports_strongest_action_support():

    tracker = AgentPerformanceTracker()

    record_action_history(
        tracker,
        "Technical Analyst",
        "BUY",
        18,
        2,
    )

    record_action_history(
        tracker,
        "Company Analyst",
        "BUY",
        10,
        10,
    )

    record_action_history(
        tracker,
        "News Analyst",
        "BUY",
        6,
        14,
    )

    engine = DecisionEngine()
    engine.agent_weight_engine = AgentWeightEngine(
        tracker
    )

    decision = engine.evaluate(
        [
            make_result(
                "Technical Analyst",
                Action.BUY,
            ),
            make_result(
                "Company Analyst",
                Action.SELL,
            ),
            make_result(
                "News Analyst",
                Action.SELL,
            ),
        ]
    )

    assert decision.action_support_analyst == (
        "Technical Analyst"
    )

    assert decision.action_support_action == (
        Action.BUY
    )

    assert decision.action_support_weight == 0.4063
