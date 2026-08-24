from datetime import datetime

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


def test_prediction_tracker_persists_and_reloads(tmp_path):
    storage_path = tmp_path / "predictions.json"

    tracker = PredictionTracker(storage_path=storage_path)
    prediction = tracker.record(
        decision=make_decision(),
        price_usd=180.25,
        reason="AI BUY prediction.",
    )

    prediction.evaluated = True
    prediction.correct = True
    prediction.evaluated_price_usd = 184.0
    prediction.price_change_percent = (
        (184.0 - 180.25) / 180.25 * 100
    )
    prediction.evaluated_at = datetime.now()

    # Persist the updated evaluation state through a fresh
    # record save cycle. This mirrors the normal tracker API.
    tracker.clear()
    tracker.record(
        decision=make_decision(),
        price_usd=180.25,
        reason="AI BUY prediction.",
    )

    reloaded = PredictionTracker(storage_path=storage_path)

    assert reloaded.count() == 1
    history = reloaded.history()
    assert history[0]["symbol"] == "NVDA"
    assert history[0]["action"] == "BUY"
    assert history[0]["price_usd"] == 180.25
    assert history[0]["reason"] == "AI BUY prediction."


def test_prediction_tracker_persists_clear(tmp_path):
    storage_path = tmp_path / "predictions.json"

    tracker = PredictionTracker(storage_path=storage_path)
    tracker.record(
        decision=make_decision(),
        price_usd=180.25,
    )

    tracker.clear()

    reloaded = PredictionTracker(storage_path=storage_path)

    assert reloaded.count() == 0
    assert reloaded.history() == []
