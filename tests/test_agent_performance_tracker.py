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


def test_tracker_records_action_specific_performance():

    tracker = AgentPerformanceTracker()

    tracker.record(
        analyst="Technical Analyst",
        correct=True,
        action="BUY",
    )

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

    performance = tracker.get(
        "Technical Analyst"
    )

    assert performance.predictions == 3
    assert performance.correct == 2
    assert performance.accuracy == 66.67

    assert performance.action_predictions["BUY"] == 3
    assert performance.action_correct["BUY"] == 2
    assert performance.action_accuracy["BUY"] == 66.67


def test_rebuild_from_predictions_preserves_action_performance():

    from atlas.trading.prediction_record import PredictionRecord
    from datetime import datetime

    tracker = AgentPerformanceTracker()

    predictions = [
        PredictionRecord(
            symbol="BTC-USD",
            action="BUY",
            confidence=90.0,
            evidence=90.0,
            price_usd=65000.0,
            timestamp=datetime.now(),
            analysts=["Technical Analyst"],
            evaluated=True,
            correct=True,
        ),
        PredictionRecord(
            symbol="BTC-USD",
            action="BUY",
            confidence=90.0,
            evidence=90.0,
            price_usd=65000.0,
            timestamp=datetime.now(),
            analysts=["Technical Analyst"],
            evaluated=True,
            correct=False,
        ),
        PredictionRecord(
            symbol="BTC-USD",
            action="SELL",
            confidence=90.0,
            evidence=90.0,
            price_usd=65000.0,
            timestamp=datetime.now(),
            analysts=["Technical Analyst"],
            evaluated=True,
            correct=True,
        ),
    ]

    tracker.rebuild_from_predictions(
        predictions
    )

    performance = tracker.get(
        "Technical Analyst"
    )

    assert performance.predictions == 3
    assert performance.correct == 2

    assert performance.action_predictions["BUY"] == 2
    assert performance.action_correct["BUY"] == 1

    assert performance.action_predictions["SELL"] == 1
    assert performance.action_correct["SELL"] == 1

    assert performance.action_accuracy["BUY"] == 50.0
    assert performance.action_accuracy["SELL"] == 100.0


def test_action_performance_survives_restart(tmp_path):

    from atlas.trading.prediction_record import PredictionRecord
    from datetime import datetime

    storage = tmp_path / "agent_performance.json"

    tracker = AgentPerformanceTracker(
        storage_path=storage
    )

    predictions = [
        PredictionRecord(
            symbol="BTC-USD",
            action="BUY",
            confidence=90.0,
            evidence=90.0,
            price_usd=65000.0,
            timestamp=datetime.now(),
            analysts=["Technical Analyst"],
            evaluated=True,
            correct=True,
        ),
        PredictionRecord(
            symbol="BTC-USD",
            action="SELL",
            confidence=90.0,
            evidence=90.0,
            price_usd=65000.0,
            timestamp=datetime.now(),
            analysts=["Technical Analyst"],
            evaluated=True,
            correct=False,
        ),
    ]

    tracker.rebuild_from_predictions(
        predictions
    )

    restarted = AgentPerformanceTracker(
        storage_path=storage
    )

    performance = restarted.get(
        "Technical Analyst"
    )

    assert performance.predictions == 2
    assert performance.correct == 1

    assert performance.action_predictions["BUY"] == 1
    assert performance.action_correct["BUY"] == 1

    assert performance.action_predictions["SELL"] == 1
    assert performance.action_correct["SELL"] == 0

    assert performance.action_accuracy["BUY"] == 100.0
    assert performance.action_accuracy["SELL"] == 0.0



def test_rebuild_from_predictions_excludes_hold_from_directional_performance():

    from atlas.trading.prediction_record import PredictionRecord
    from datetime import datetime

    tracker = AgentPerformanceTracker()

    tracker.rebuild_from_predictions(
        [
            PredictionRecord(
                symbol="BTC-USD",
                action="HOLD",
                confidence=80.0,
                evidence=75.0,
                price_usd=65000.0,
                timestamp=datetime.now(),
                analysts=["Technical Analyst"],
                evaluated=True,
                correct=True,
            ),
            PredictionRecord(
                symbol="BTC-USD",
                action="BUY",
                confidence=90.0,
                evidence=90.0,
                price_usd=65000.0,
                timestamp=datetime.now(),
                analysts=["Technical Analyst"],
                evaluated=True,
                correct=True,
            ),
        ]
    )

    performance = tracker.get("Technical Analyst")

    assert performance.predictions == 2
    assert performance.correct == 2
    assert performance.action_predictions == {"BUY": 1}
    assert performance.action_correct == {"BUY": 1}
