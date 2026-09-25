from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult
from atlas.trading.prediction_tracker import PredictionTracker


def make_decision():
    return DecisionResult(
        symbol="NVDA",
        action=Action.BUY,
        confidence=87.5,
        evidence=82.0,
        analysts=[
            "Technical Analyst",
            "News Analyst",
            "Company Analyst",
        ],
        reasoning=[
            "Strong technical trend.",
            "Positive company fundamentals.",
        ],
    )


def test_prediction_tracker_records_prediction():
    tracker = PredictionTracker()

    decision = make_decision()

    prediction = tracker.record(
        decision=decision,
        price_usd=180.25,
        reason="AI BUY prediction.",
    )

    assert prediction.symbol == "NVDA"
    assert prediction.action == "BUY"
    assert prediction.confidence == 87.5
    assert prediction.evidence == 82.0
    assert prediction.price_usd == 180.25
    assert prediction.reason == "AI BUY prediction."

    assert tracker.count() == 1


def test_prediction_tracker_history():
    tracker = PredictionTracker()

    decision = make_decision()

    tracker.record(
        decision=decision,
        price_usd=180.25,
    )

    history = tracker.history()

    assert len(history) == 1
    assert history[0]["symbol"] == "NVDA"
    assert history[0]["action"] == "BUY"
    assert history[0]["confidence"] == 87.5
    assert history[0]["evidence"] == 82.0
    assert history[0]["price_usd"] == 180.25


def test_prediction_tracker_clear():
    tracker = PredictionTracker()

    tracker.record(
        decision=make_decision(),
        price_usd=180.25,
    )

    assert tracker.count() == 1

    tracker.clear()

    assert tracker.count() == 0
    assert tracker.history() == []


def test_prediction_tracker_preserves_analysis_snapshot_reference():
    tracker = PredictionTracker()

    decision = make_decision()
    decision.analysis_snapshot_id = 42

    prediction = tracker.record(
        decision=decision,
        price_usd=180.25,
    )

    assert prediction.analysis_snapshot_id == 42


def test_prediction_tracker_persists_analysis_snapshot_reference(tmp_path):
    database_path = tmp_path / "atlas.db"
    tracker = PredictionTracker(storage_path=database_path)

    decision = make_decision()
    decision.analysis_snapshot_id = 42

    tracker.record(
        decision=decision,
        price_usd=180.25,
    )

    restarted_tracker = PredictionTracker(
        storage_path=database_path,
    )
    prediction = restarted_tracker.repository.get_all()[0]

    assert prediction.analysis_snapshot_id == 42
