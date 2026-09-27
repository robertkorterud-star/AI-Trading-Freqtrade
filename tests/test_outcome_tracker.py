from datetime import datetime

from atlas.database.connection import Database
from atlas.database.outcome_repository import OutcomeRepository
from atlas.database.schema import initialize_database
from atlas.trading.outcome_tracker import OutcomeRecord, OutcomeTracker
from atlas.trading.prediction_record import PredictionRecord


def make_prediction(action, price=100.0):
    return PredictionRecord(
        symbol="NVDA",
        action=action,
        confidence=85.0,
        evidence=80.0,
        price_usd=price,
        timestamp=datetime.now(),
        reason="Test prediction.",
    )


def test_buy_prediction_is_correct_when_price_rises():
    tracker = OutcomeTracker()

    outcome = tracker.evaluate(
        prediction=make_prediction("BUY"),
        current_price_usd=105.0,
    )

    assert outcome.correct is True
    assert outcome.change_percent == 5.0


def test_sell_prediction_is_correct_when_price_falls():
    tracker = OutcomeTracker()

    outcome = tracker.evaluate(
        prediction=make_prediction("SELL"),
        current_price_usd=95.0,
    )

    assert outcome.correct is True
    assert outcome.change_percent == -5.0


def test_hold_prediction_is_correct_when_price_is_stable():
    tracker = OutcomeTracker()

    outcome = tracker.evaluate(
        prediction=make_prediction("HOLD"),
        current_price_usd=100.5,
    )

    assert outcome.correct is True


def test_tracker_calculates_accuracy():
    tracker = OutcomeTracker()

    tracker.evaluate(
        prediction=make_prediction("BUY"),
        current_price_usd=105.0,
    )

    tracker.evaluate(
        prediction=make_prediction("BUY"),
        current_price_usd=95.0,
    )

    assert tracker.count() == 2
    assert tracker.correct_count() == 1
    assert tracker.accuracy() == 50.0


def test_tracker_history():
    tracker = OutcomeTracker()

    tracker.evaluate(
        prediction=make_prediction("BUY"),
        current_price_usd=105.0,
    )

    history = tracker.history()

    assert len(history) == 1
    assert history[0]["symbol"] == "NVDA"
    assert history[0]["action"] == "BUY"
    assert history[0]["change_percent"] == 5.0
    assert history[0]["correct"] is True


def test_tracker_clear():
    tracker = OutcomeTracker()

    tracker.evaluate(
        prediction=make_prediction("BUY"),
        current_price_usd=105.0,
    )

    tracker.clear()

    assert tracker.count() == 0
    assert tracker.history() == []



def test_outcome_repository_preserves_subsecond_latest_order(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)
    repository = OutcomeRepository(database)

    newer = OutcomeRecord(
        symbol="NVDA",
        action="BUY",
        prediction_price_usd=100.0,
        outcome_price_usd=105.0,
        change_percent=5.0,
        correct=True,
        timestamp=datetime(2026, 9, 28, 8, 0, 0, 900000),
    )
    repository.save(1, newer)

    older = OutcomeRecord(
        symbol="NVDA",
        action="BUY",
        prediction_price_usd=100.0,
        outcome_price_usd=104.0,
        change_percent=4.0,
        correct=True,
        timestamp=datetime(2026, 9, 28, 8, 0, 0, 100000),
    )
    repository.save(1, older)

    outcomes = repository.get_all()

    assert outcomes[0].timestamp == newer.timestamp
