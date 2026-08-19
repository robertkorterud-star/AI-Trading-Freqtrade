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


def test_weights_are_stable_with_small_accuracy_difference():
    tracker = AgentPerformanceTracker()

    # All analysts have enough history.
    # Their accuracy is intentionally close.
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
        "Company Analyst",
        True,
        17,
    )
    add_predictions(
        tracker,
        "Company Analyst",
        False,
        3,
    )

    add_predictions(
        tracker,
        "News Analyst",
        True,
        16,
    )
    add_predictions(
        tracker,
        "News Analyst",
        False,
        4,
    )

    weights = AgentWeightEngine(tracker).calculate()

    # The best analyst may lead, but no analyst should
    # dominate simply because of a small accuracy difference.
    assert max(weights.values()) - min(weights.values()) < 0.10


def test_weights_remain_within_safety_limits_after_stabilization():
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

    add_predictions(
        tracker,
        "Company Analyst",
        True,
        10,
    )
    add_predictions(
        tracker,
        "Company Analyst",
        False,
        10,
    )

    weights = AgentWeightEngine(tracker).calculate()

    assert round(sum(weights.values()), 4) == 1.0

    for weight in weights.values():
        assert 0.10 <= weight <= 0.60


def test_weights_do_not_overreact_to_one_recent_result():
    tracker = AgentPerformanceTracker()

    # Establish a strong but realistic historical baseline.
    for analyst in (
        "Technical Analyst",
        "Company Analyst",
        "News Analyst",
    ):
        add_predictions(
            tracker,
            analyst,
            True,
            18,
        )
        add_predictions(
            tracker,
            analyst,
            False,
            2,
        )

    before = AgentWeightEngine(tracker).calculate()

    # One additional incorrect prediction should not
    # radically change an analyst's weight.
    tracker.record(
        analyst="Technical Analyst",
        correct=False,
    )

    after = AgentWeightEngine(tracker).calculate()

    assert abs(
        after["Technical Analyst"]
        - before["Technical Analyst"]
    ) < 0.05


def test_weights_sum_to_exactly_one_after_rounding():
    tracker = AgentPerformanceTracker()

    add_predictions(
        tracker,
        "Technical Analyst",
        True,
        20,
    )

    add_predictions(
        tracker,
        "Company Analyst",
        True,
        20,
    )

    add_predictions(
        tracker,
        "News Analyst",
        True,
        20,
    )

    weights = AgentWeightEngine(tracker).calculate()

    assert sum(weights.values()) == 1.0
