from atlas.algorithms.decision_core import DecisionCore
from atlas.trading.agent_performance_tracker import AgentPerformanceTracker
from atlas.trading.agent_weight_engine import AgentWeightEngine


def test_learned_agent_weight_changes_decision_integration():
    tracker = AgentPerformanceTracker()

    for _ in range(20):
        tracker.record(
            "Technical Analyst",
            True,
            action="BUY",
        )

    for _ in range(20):
        tracker.record(
            "News Analyst",
            False,
            action="BUY",
        )

    engine = AgentWeightEngine(tracker)

    weights = engine.calculate(action="BUY")

    assert weights["Technical Analyst"] > weights["News Analyst"]

    core = DecisionCore(
        agent_weight_engine=engine,
    )

    technical_weight = core._signal_weight(
        type(
            "Signal",
            (),
            {"algorithm": "agent:Technical Analyst"},
        )(),
        action_value="BUY",
    )

    news_weight = core._signal_weight(
        type(
            "Signal",
            (),
            {"algorithm": "agent:News Analyst"},
        )(),
        action_value="BUY",
    )

    assert technical_weight == weights["Technical Analyst"]
    assert news_weight == weights["News Analyst"]
    assert technical_weight > news_weight
