from datetime import datetime, timedelta

from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult
from atlas.trading.outcome_tracker import OutcomeTracker
from atlas.trading.prediction_evaluator import PredictionEvaluator
from atlas.trading.prediction_tracker import PredictionTracker


def test_evaluator_finds_old_predictions():
    predictions = PredictionTracker()
    outcomes = OutcomeTracker()

    decision = DecisionResult(
        symbol="NVDA",
        action=Action.BUY,
        confidence=88.0,
        evidence=85.0,
    )

    prediction = predictions.record(
        decision=decision,
        price_usd=180.0,
    )

    prediction.timestamp = (
        datetime.now() - timedelta(hours=25)
    )

    evaluator = PredictionEvaluator(
        predictions=predictions,
        outcomes=outcomes,
    )

    ready = evaluator.ready_predictions(
        hours=24,
    )

    assert len(ready) == 1
    assert ready[0] is prediction


def test_evaluator_ignores_recent_predictions():
    predictions = PredictionTracker()
    outcomes = OutcomeTracker()

    decision = DecisionResult(
        symbol="NVDA",
        action=Action.BUY,
        confidence=88.0,
        evidence=85.0,
    )

    prediction = predictions.record(
        decision=decision,
        price_usd=180.0,
    )

    evaluator = PredictionEvaluator(
        predictions=predictions,
        outcomes=outcomes,
    )

    ready = evaluator.ready_predictions(
        hours=24,
    )

    assert len(ready) == 0


def test_evaluator_creates_outcome():
    predictions = PredictionTracker()
    outcomes = OutcomeTracker()

    decision = DecisionResult(
        symbol="NVDA",
        action=Action.BUY,
        confidence=88.0,
        evidence=85.0,
    )

    prediction = predictions.record(
        decision=decision,
        price_usd=180.0,
    )

    evaluator = PredictionEvaluator(
        predictions=predictions,
        outcomes=outcomes,
    )

    outcome = evaluator.evaluate(
        prediction=prediction,
        current_price_usd=190.0,
    )

    assert outcome.symbol == "NVDA"
    assert outcome.action == "BUY"
    assert outcome.correct is True
    assert outcomes.count() == 1


def test_evaluator_updates_agent_performance():
    predictions = PredictionTracker()
    outcomes = OutcomeTracker()

    decision = DecisionResult(
        symbol="NVDA",
        action=Action.BUY,
        confidence=88.0,
        evidence=85.0,
        analysts=[
            "Technical Analyst",
            "News Analyst",
            "Company Analyst",
        ],
    )

    prediction = predictions.record(
        decision=decision,
        price_usd=180.0,
    )

    evaluator = PredictionEvaluator(
        predictions=predictions,
        outcomes=outcomes,
    )

    outcome = evaluator.evaluate(
        prediction=prediction,
        current_price_usd=190.0,
    )

    assert outcome.correct is True

    performance = evaluator.agent_performance

    assert performance.count() == 3

    technical = performance.get(
        "Technical Analyst"
    )
    news = performance.get(
        "News Analyst"
    )
    company = performance.get(
        "Company Analyst"
    )

    assert technical.predictions == 1
    assert technical.correct == 1
    assert technical.accuracy == 100.0

    assert news.predictions == 1
    assert news.correct == 1

    assert company.predictions == 1
    assert company.correct == 1
