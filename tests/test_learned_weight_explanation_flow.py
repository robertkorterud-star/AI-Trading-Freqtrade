from datetime import datetime

from atlas.decision.engine import DecisionEngine
from atlas.decision.explanation import explain_decision
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult
from atlas.trading.agent_performance_tracker import (
    AgentPerformanceTracker,
)
from atlas.trading.agent_weight_engine import AgentWeightEngine


def test_learned_weight_flows_into_decision_explanation():

    tracker = AgentPerformanceTracker()

    # Technical Analyst has established strong historical
    # performance while News Analyst has weaker performance.
    for _ in range(19):
        tracker.record(
            analyst="Technical Analyst",
            correct=True,
            action="BUY",
        )

    tracker.record(
        analyst="Technical Analyst",
        correct=False,
        action="BUY",
    )
    tracker.record(
        analyst="Technical Analyst",
        correct=True,
        action="BUY",
    )

    for _ in range(19):
        tracker.record(
            analyst="News Analyst",
            correct=True,
            action="BUY",
        )

    for _ in range(1):
        tracker.record(
            analyst="News Analyst",
            correct=False,
            action="BUY",
        )

    weight_engine = AgentWeightEngine(tracker)

    weights = weight_engine.calculate(
        action="BUY",
    )

    assert (
        weights["Technical Analyst"]
        > weights["News Analyst"]
    )

    engine = DecisionEngine()
    engine.agent_weight_engine = weight_engine

    results = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Technical Analyst",
            action=Action.BUY,
            confidence=90.0,
            evidence=90.0,
            reasoning=[
                "Strong technical evidence."
            ],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="News Analyst",
            action=Action.SELL,
            confidence=70.0,
            evidence=70.0,
            reasoning=[
                "Negative news evidence."
            ],
        ),
    ]

    decision = engine.evaluate(results)

    explanation = explain_decision(
        decision,
        agreement=50.0,
    )

    assert decision.agent_weights

    assert (
        decision.agent_weights["Technical Analyst"]
        > decision.agent_weights["News Analyst"]
    )

    assert explanation.dominant_action is not None
    assert explanation.dominant_weight > 0.0

    assert (
        explanation.action_support_analyst
        is not None
    )

    assert (
        explanation.action_support_action
        is not None
    )

    assert (
        explanation.action_support_weight
        > 0.0
    )

    assert any(
        "learned support" in reason.lower()
        for reason in explanation.key_reasons
    )

    assert any(
        "adaptive analyst weights" in reason.lower()
        for reason in explanation.key_reasons
    )
