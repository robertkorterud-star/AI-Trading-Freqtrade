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

    assert sum(weights.values()) == 1.0

    assert weights["Technical Analyst"] in (
        0.3333,
        0.3334,
    )

    assert weights["News Analyst"] in (
        0.3333,
        0.3334,
    )

    assert weights["Company Analyst"] in (
        0.3333,
        0.3334,
    )


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


def test_action_specific_weights_follow_action_accuracy():

    tracker = AgentPerformanceTracker()

    # Technical Analyst:
    # BUY = 18/20 correct = 90%
    # SELL = 6/20 correct = 30%
    for _ in range(18):
        tracker.record(
            analyst="Technical Analyst",
            correct=True,
            action="BUY",
        )

    for _ in range(2):
        tracker.record(
            analyst="Technical Analyst",
            correct=False,
            action="BUY",
        )

    for _ in range(6):
        tracker.record(
            analyst="Technical Analyst",
            correct=True,
            action="SELL",
        )

    for _ in range(14):
        tracker.record(
            analyst="Technical Analyst",
            correct=False,
            action="SELL",
        )

    # Company Analyst:
    # BUY = 10/20 = 50%
    # SELL = 10/20 = 50%
    for _ in range(10):
        tracker.record(
            analyst="Company Analyst",
            correct=True,
            action="BUY",
        )

    for _ in range(10):
        tracker.record(
            analyst="Company Analyst",
            correct=False,
            action="BUY",
        )

    for _ in range(10):
        tracker.record(
            analyst="Company Analyst",
            correct=True,
            action="SELL",
        )

    for _ in range(10):
        tracker.record(
            analyst="Company Analyst",
            correct=False,
            action="SELL",
        )

    # News Analyst:
    # BUY = 6/20 = 30%
    # SELL = 18/20 = 90%
    for _ in range(6):
        tracker.record(
            analyst="News Analyst",
            correct=True,
            action="BUY",
        )

    for _ in range(14):
        tracker.record(
            analyst="News Analyst",
            correct=False,
            action="BUY",
        )

    for _ in range(18):
        tracker.record(
            analyst="News Analyst",
            correct=True,
            action="SELL",
        )

    for _ in range(2):
        tracker.record(
            analyst="News Analyst",
            correct=False,
            action="SELL",
        )

    engine = AgentWeightEngine(tracker)

    buy_weights = engine.calculate(
        action="BUY",
    )

    sell_weights = engine.calculate(
        action="SELL",
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

    assert round(
        sum(buy_weights.values()),
        4,
    ) == 1.0

    assert round(
        sum(sell_weights.values()),
        4,
    ) == 1.0

    for weight in buy_weights.values():
        assert 0.10 <= weight <= 0.60

    for weight in sell_weights.values():
        assert 0.10 <= weight <= 0.60


def test_weight_explanations_are_empty_without_history():

    tracker = AgentPerformanceTracker()

    explanations = AgentWeightEngine(
        tracker
    ).explain()

    assert explanations == {}


def test_weight_explanations_show_building_history():

    tracker = AgentPerformanceTracker()

    add_predictions(
        tracker,
        "Technical Analyst",
        True,
        10,
    )

    add_predictions(
        tracker,
        "Company Analyst",
        False,
        10,
    )

    add_predictions(
        tracker,
        "News Analyst",
        True,
        10,
    )

    explanations = AgentWeightEngine(
        tracker
    ).explain()

    technical = explanations[
        "Technical Analyst"
    ]

    assert technical["status"] == "building_history"
    assert technical["predictions"] == 10
    assert technical["stabilized_accuracy"] is None
    assert technical["weight"] == 0.3333 or (
        technical["weight"] == 0.3334
    )
    assert "20 predictions" in technical["reason"]


def test_weight_explanations_show_adaptive_reason():

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

    add_predictions(
        tracker,
        "News Analyst",
        True,
        6,
    )

    add_predictions(
        tracker,
        "News Analyst",
        False,
        14,
    )

    explanations = AgentWeightEngine(
        tracker
    ).explain()

    technical = explanations[
        "Technical Analyst"
    ]

    news = explanations[
        "News Analyst"
    ]

    assert technical["status"] == "adaptive"
    assert news["status"] == "adaptive"

    assert technical["comparison"] == "above_average"
    assert news["comparison"] == "below_average"

    assert (
        technical["stabilized_accuracy"]
        > news["stabilized_accuracy"]
    )

    assert (
        technical["weight"]
        > news["weight"]
    )

    assert technical["average_stabilized_accuracy"] is not None
    assert "Higher weight" in technical["reason"]
    assert "Lower weight" in news["reason"]


def test_weight_explanation_reports_safety_limit():

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
        False,
        20,
    )

    engine = AgentWeightEngine(
        tracker
    )

    explanations = engine.explain()

    technical = explanations[
        "Technical Analyst"
    ]

    assert technical["status"] == "adaptive"
    assert technical["weight"] <= engine.MAX_WEIGHT
    assert technical["limit"] in (
        None,
        "maximum",
    )


def test_weight_explanations_support_action_specific_history():

    tracker = AgentPerformanceTracker()

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

    for _ in range(19):
        tracker.record(
            analyst="News Analyst",
            correct=False,
            action="BUY",
        )

    tracker.record(
        analyst="News Analyst",
        correct=True,
        action="BUY",
    )

    engine = AgentWeightEngine(tracker)

    explanations = engine.explain(
        action="BUY",
    )

    technical = explanations["Technical Analyst"]
    news = explanations["News Analyst"]

    assert technical["predictions"] == 20
    assert technical["accuracy"] == 95.0

    assert news["predictions"] == 20
    assert news["accuracy"] == 5.0

    assert (
        technical["weight"]
        > news["weight"]
    )

    assert technical["status"] == "adaptive"
    assert news["status"] == "adaptive"

    assert (
        technical["stabilized_accuracy"]
        > news["stabilized_accuracy"]
    )


def test_weight_explanations_action_history_can_be_building():

    tracker = AgentPerformanceTracker()

    for _ in range(10):
        tracker.record(
            analyst="Technical Analyst",
            correct=True,
            action="BUY",
        )

    for _ in range(20):
        tracker.record(
            analyst="Technical Analyst",
            correct=True,
            action="SELL",
        )

    engine = AgentWeightEngine(tracker)

    explanations = engine.explain(
        action="BUY",
    )

    technical = explanations["Technical Analyst"]

    assert technical["predictions"] == 10
    assert technical["accuracy"] == 100.0
    assert technical["status"] == "building_history"
    assert technical["stabilized_accuracy"] is None
    assert technical["comparison"] is None
    assert technical["limit"] is None


def test_action_specific_weight_explanation_mentions_action_context():

    tracker = AgentPerformanceTracker()

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

    for _ in range(19):
        tracker.record(
            analyst="News Analyst",
            correct=False,
            action="BUY",
        )

    tracker.record(
        analyst="News Analyst",
        correct=True,
        action="BUY",
    )

    engine = AgentWeightEngine(tracker)

    explanations = engine.explain(
        action="BUY",
    )

    technical = explanations["Technical Analyst"]

    assert technical["predictions"] == 20
    assert technical["accuracy"] == 95.0
    assert technical["weight"] > 0.0

    assert (
        "BUY" in technical["reason"]
        or "buy" in technical["reason"].lower()
    )
