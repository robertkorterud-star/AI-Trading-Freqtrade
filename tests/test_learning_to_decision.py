from atlas.decision.engine import DecisionEngine
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult
from atlas.trading.agent_performance_tracker import AgentPerformanceTracker
from atlas.trading.agent_weight_engine import AgentWeightEngine


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
