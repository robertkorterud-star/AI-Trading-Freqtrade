from atlas.trading.agent_performance_tracker import (
    AgentPerformanceTracker,
)


def test_tracker_records_correct_prediction():
    tracker = AgentPerformanceTracker()

    performance = tracker.record(
        analyst="Technical Analyst",
        correct=True,
    )

    assert performance.analyst == "Technical Analyst"
    assert performance.predictions == 1
    assert performance.correct == 1
    assert performance.wrong == 0
    assert performance.accuracy == 100.0


def test_tracker_records_wrong_prediction():
    tracker = AgentPerformanceTracker()

    tracker.record(
        analyst="News Analyst",
        correct=False,
    )

    performance = tracker.get(
        "News Analyst"
    )

    assert performance.predictions == 1
    assert performance.correct == 0
    assert performance.wrong == 1
    assert performance.accuracy == 0.0


def test_tracker_calculates_accuracy():
    tracker = AgentPerformanceTracker()

    tracker.record(
        analyst="Company Analyst",
        correct=True,
    )

    tracker.record(
        analyst="Company Analyst",
        correct=True,
    )

    tracker.record(
        analyst="Company Analyst",
        correct=False,
    )

    performance = tracker.get(
        "Company Analyst"
    )

    assert performance.predictions == 3
    assert performance.correct == 2
    assert performance.wrong == 1
    assert performance.accuracy == 66.67


def test_tracker_supports_multiple_analysts():
    tracker = AgentPerformanceTracker()

    tracker.record(
        analyst="Technical Analyst",
        correct=True,
    )

    tracker.record(
        analyst="News Analyst",
        correct=False,
    )

    tracker.record(
        analyst="Company Analyst",
        correct=True,
    )

    assert tracker.count() == 3

    history = tracker.history()

    assert len(history) == 3


def test_tracker_history_contains_metrics():
    tracker = AgentPerformanceTracker()

    tracker.record(
        analyst="Technical Analyst",
        correct=True,
    )

    history = tracker.history()

    assert history[0]["analyst"] == (
        "Technical Analyst"
    )

    assert history[0]["predictions"] == 1
    assert history[0]["correct"] == 1
    assert history[0]["wrong"] == 0
    assert history[0]["accuracy"] == 100.0


def test_tracker_clear():
    tracker = AgentPerformanceTracker()

    tracker.record(
        analyst="Technical Analyst",
        correct=True,
    )

    tracker.clear()

    assert tracker.count() == 0
    assert tracker.history() == []
