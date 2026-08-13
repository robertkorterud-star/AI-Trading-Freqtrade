from atlas.trading.agent_performance_tracker import (
    AgentPerformanceTracker,
)
from atlas.trading.agent_weight_engine import (
    AgentWeightEngine,
)


def add_predictions(
    tracker,
    analyst,
    correct,
    total=10,
):
    for _ in range(total):
        tracker.record(
            analyst=analyst,
            correct=correct,
        )


def test_weights_are_equal_with_insufficient_history():
    tracker = AgentPerformanceTracker()

    add_predictions(
        tracker,
        "Technical Analyst",
        True,
        10,
    )

    add_predictions(
        tracker,
        "News Analyst",
        False,
        10,
    )

    add_predictions(
        tracker,
        "Company Analyst",
        True,
        10,
    )

    engine = AgentWeightEngine(tracker)

    weights = engine.calculate()

    assert weights["Technical Analyst"] == 0.3333
    assert weights["News Analyst"] == 0.3333
    assert weights["Company Analyst"] == 0.3333


def test_weights_follow_accuracy_after_minimum_history():
    tracker = AgentPerformanceTracker()

    add_predictions(
        tracker,
        "Technical Analyst",
        True,
        18,
    )
    add_predictions(
        tracker,
        "Technical Analyst",
        False,
        2,
    )

    add_predictions(
        tracker,
        "News Analyst",
        True,
        10,
    )
    add_predictions(
        tracker,
        "News Analyst",
        False,
        10,
    )

    add_predictions(
        tracker,
        "Company Analyst",
        True,
        14,
    )
    add_predictions(
        tracker,
        "Company Analyst",
        False,
        6,
    )

    engine = AgentWeightEngine(tracker)

    weights = engine.calculate()

    assert weights["Technical Analyst"] > weights["Company Analyst"]
    assert weights["Company Analyst"] > weights["News Analyst"]


def test_weights_sum_to_one():
    tracker = AgentPerformanceTracker()

    add_predictions(
        tracker,
        "Technical Analyst",
        True,
        20,
    )

    add_predictions(
        tracker,
        "News Analyst",
        True,
        10,
    )
    add_predictions(
        tracker,
        "News Analyst",
        False,
        10,
    )

    add_predictions(
        tracker,
        "Company Analyst",
        True,
        16,
    )
    add_predictions(
        tracker,
        "Company Analyst",
        False,
        4,
    )

    engine = AgentWeightEngine(tracker)

    weights = engine.calculate()

    assert round(sum(weights.values()), 4) == 1.0


def test_weights_have_safety_limits():
    tracker = AgentPerformanceTracker()

    add_predictions(
        tracker,
        "Technical Analyst",
        True,
        20,
    )

    add_predictions(
        tracker,
        "News Analyst",
        False,
        20,
    )

    engine = AgentWeightEngine(tracker)

    weights = engine.calculate()

    for weight in weights.values():
        assert weight >= 0.10
        assert weight <= 0.60


def test_empty_tracker_returns_empty_weights():
    tracker = AgentPerformanceTracker()

    engine = AgentWeightEngine(tracker)

    assert engine.calculate() == {}
