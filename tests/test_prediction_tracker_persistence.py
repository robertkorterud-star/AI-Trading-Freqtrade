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

    reloaded = PredictionTracker(storage_path=storage_path)

    assert reloaded.count() == 1
    history = reloaded.history()
    assert history[0]["symbol"] == "NVDA"
    assert history[0]["action"] == "BUY"
    assert history[0]["price_usd"] == 180.25
    assert history[0]["reason"] == "AI BUY prediction."
    assert prediction.as_dict() == history[0]


def test_prediction_tracker_persists_evaluated_state(tmp_path):
    storage_path = tmp_path / "predictions.json"

    tracker = PredictionTracker(storage_path=storage_path)
    prediction = tracker.record(
        decision=make_decision(),
        price_usd=180.25,
    )

    prediction.evaluated = True
    prediction.correct = True
    prediction.evaluated_price_usd = 184.0
    prediction.price_change_percent = (
        (184.0 - 180.25) / 180.25 * 100
    )
    tracker.save()

    reloaded = PredictionTracker(storage_path=storage_path)
    loaded = reloaded.history()[0]

    assert loaded["evaluated"] is True
    assert loaded["correct"] is True
    assert loaded["evaluated_price_usd"] == 184.0
    assert loaded["price_change_percent"] == round(
        prediction.price_change_percent,
        2,
    )


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
