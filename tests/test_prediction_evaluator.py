from datetime import datetime, timedelta

import pytest

from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult
from atlas.database.outcome_repository import OutcomeRepository
from atlas.trading.agent_performance_tracker import (
    AgentPerformanceTracker,
)
from atlas.trading.outcome_tracker import OutcomeTracker
from atlas.trading.prediction_evaluator import PredictionEvaluator
from atlas.trading.prediction_record import PredictionRecord
from atlas.trading.prediction_tracker import PredictionTracker


def _persisted_old_prediction(database_path, analysts=None):
    tracker = PredictionTracker(
        storage_path=database_path,
    )

    prediction = PredictionRecord(
        symbol="NVDA",
        action="BUY",
        confidence=88.0,
        evidence=85.0,
        price_usd=180.0,
        timestamp=datetime.now() - timedelta(hours=25),
        analysts=analysts or [],
    )

    tracker.repository.save(prediction)

    return tracker, prediction


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


def test_evaluated_prediction_persists_outcome(tmp_path):
    database_path = tmp_path / "atlas.db"
    performance_path = tmp_path / "agent_performance.json"
    tracker, prediction = _persisted_old_prediction(
        database_path,
        analysts=["Technical Analyst"],
    )
    outcome_repository = OutcomeRepository(
        tracker.database
    )
    evaluator = PredictionEvaluator(
        predictions=tracker,
        outcomes=OutcomeTracker(),
        agent_performance=AgentPerformanceTracker(
            storage_path=performance_path,
        ),
        outcome_repository=outcome_repository,
    )

    outcome = evaluator.evaluate(
        prediction=prediction,
        current_price_usd=190.0,
    )

    stored_outcomes = outcome_repository.get_for_prediction(
        prediction.database_id
    )

    assert outcome is not None
    assert len(stored_outcomes) == 1
    assert stored_outcomes[0].correct is True

    stored_prediction = tracker.repository.get_all()[0]

    assert stored_prediction.evaluated is True
    assert stored_prediction.correct is True
    assert evaluator.agent_performance.get(
        "Technical Analyst"
    ).predictions == 1


def test_failed_outcome_persistence_rolls_back_prediction_update(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "atlas.db"
    performance_path = tmp_path / "agent_performance.json"
    tracker, prediction = _persisted_old_prediction(
        database_path,
        analysts=["Technical Analyst"],
    )
    outcome_repository = OutcomeRepository(tracker.database)
    performance = AgentPerformanceTracker(
        storage_path=performance_path,
    )
    evaluator = PredictionEvaluator(
        predictions=tracker,
        outcomes=OutcomeTracker(),
        agent_performance=performance,
        outcome_repository=outcome_repository,
    )

    def fail_save(*args, **kwargs):
        raise RuntimeError("Outcome persistence failed.")

    monkeypatch.setattr(
        outcome_repository,
        "save",
        fail_save,
    )

    with pytest.raises(
        RuntimeError,
        match="Outcome persistence failed.",
    ):
        evaluator.evaluate(
            prediction=prediction,
            current_price_usd=190.0,
        )

    stored_prediction = tracker.repository.get_all()[0]

    assert stored_prediction.evaluated is False
    assert stored_prediction.correct is None
    assert outcome_repository.count() == 0
    assert performance.get("Technical Analyst") is None


def test_evaluated_prediction_is_not_re_evaluated_after_restart(
    tmp_path,
):
    database_path = tmp_path / "atlas.db"
    tracker, _ = _persisted_old_prediction(database_path)
    outcome_repository = OutcomeRepository(tracker.database)

    first_evaluator = PredictionEvaluator(
        predictions=tracker,
        outcomes=OutcomeTracker(),
        outcome_repository=outcome_repository,
    )

    assert len(
        first_evaluator.evaluate_ready(
            current_prices_usd={"NVDA": 190.0}
        )
    ) == 1

    restarted_tracker = PredictionTracker(
        storage_path=database_path,
    )
    restarted_evaluator = PredictionEvaluator(
        predictions=restarted_tracker,
        outcomes=OutcomeTracker(),
        outcome_repository=OutcomeRepository(
            restarted_tracker.database
        ),
    )

    assert restarted_evaluator.evaluate_ready(
        current_prices_usd={"NVDA": 195.0}
    ) == []
    assert outcome_repository.count() == 1


def test_agent_performance_is_not_double_counted_after_restart(
    tmp_path,
):
    database_path = tmp_path / "atlas.db"
    performance_path = tmp_path / "agent_performance.json"
    tracker, _ = _persisted_old_prediction(
        database_path,
        analysts=["Technical Analyst"],
    )
    performance = AgentPerformanceTracker(
        storage_path=performance_path,
    )

    PredictionEvaluator(
        predictions=tracker,
        outcomes=OutcomeTracker(),
        agent_performance=performance,
        outcome_repository=OutcomeRepository(tracker.database),
    ).evaluate_ready(
        current_prices_usd={"NVDA": 190.0}
    )

    restarted_tracker = PredictionTracker(
        storage_path=database_path,
    )
    restarted_performance = AgentPerformanceTracker(
        storage_path=performance_path,
    )

    assert PredictionEvaluator(
        predictions=restarted_tracker,
        outcomes=OutcomeTracker(),
        agent_performance=restarted_performance,
        outcome_repository=OutcomeRepository(
            restarted_tracker.database
        ),
    ).evaluate_ready(
        current_prices_usd={"NVDA": 195.0}
    ) == []

    technical = restarted_performance.get("Technical Analyst")

    assert technical.predictions == 1
    assert technical.correct == 1


def test_evaluator_rebuilds_missing_performance_on_restart(
    tmp_path,
):
    database_path = tmp_path / "atlas.db"
    performance_path = tmp_path / "agent_performance.json"
    tracker, prediction = _persisted_old_prediction(
        database_path,
        analysts=["Technical Analyst", "News Analyst"],
    )

    prediction.evaluated = True
    prediction.correct = True
    prediction.evaluated_price_usd = 190.0
    prediction.evaluated_at = datetime.now()
    tracker.repository.update(
        prediction.database_id,
        prediction,
    )

    performance = AgentPerformanceTracker(
        storage_path=performance_path,
    )

    evaluator = PredictionEvaluator(
        predictions=PredictionTracker(
            storage_path=database_path,
        ),
        outcomes=OutcomeTracker(),
        agent_performance=performance,
        outcome_repository=OutcomeRepository(tracker.database),
    )

    technical = evaluator.agent_performance.get(
        "Technical Analyst"
    )
    news = evaluator.agent_performance.get("News Analyst")

    assert technical.predictions == 1
    assert technical.correct == 1
    assert news.predictions == 1
    assert news.correct == 1

    evaluator._reconcile_agent_performance()

    rebuilt_technical = evaluator.agent_performance.get(
        "Technical Analyst"
    )
    rebuilt_news = evaluator.agent_performance.get("News Analyst")

    assert rebuilt_technical.predictions == 1
    assert rebuilt_news.predictions == 1


def test_evaluator_resolves_original_analysis_snapshot(tmp_path):
    from atlas.database.analysis_snapshot_repository import (
        AnalysisSnapshotRepository,
    )
    from atlas.models.analysis_snapshot import AnalysisSnapshot

    database_path = tmp_path / "atlas.db"
    tracker = PredictionTracker(storage_path=database_path)
    snapshot_repository = AnalysisSnapshotRepository(
        tracker.database
    )
    snapshot = AnalysisSnapshot(
        database_id=None,
        symbol="NVDA",
        timestamp=datetime.now(),
        provider="test",
        model="test",
        results=[{"analyst": "Technical Analyst"}],
        decision={
            "action": "BUY",
            "confidence": 88.0,
            "evidence": 85.0,
        },
        intelligence={
            "action": "BUY",
            "buy_count": 1,
            "hold_count": 0,
            "sell_count": 0,
            "agreement": 100.0,
        },
    )
    snapshot_repository.save(snapshot)

    decision = DecisionResult(
        symbol="NVDA",
        action=Action.BUY,
        confidence=88.0,
        evidence=85.0,
        analysis_snapshot_id=snapshot.database_id,
    )
    prediction = tracker.record(
        decision=decision,
        price_usd=180.0,
    )

    evaluator = PredictionEvaluator(
        predictions=tracker,
        outcomes=OutcomeTracker(),
    )

    resolved = evaluator.analysis_snapshot_for(
        prediction
    )

    assert resolved.database_id == snapshot.database_id
    assert resolved.results == snapshot.results



def test_hold_prediction_learning_does_not_train_directional_agent_weights():
    predictions = PredictionTracker()
    outcomes = OutcomeTracker()
    performance = AgentPerformanceTracker()

    decision = DecisionResult(
        symbol="NVDA",
        action=Action.HOLD,
        confidence=88.0,
        evidence=85.0,
        analysts=["Technical Analyst"],
    )

    prediction = predictions.record(
        decision=decision,
        price_usd=180.0,
    )

    evaluator = PredictionEvaluator(
        predictions=predictions,
        outcomes=outcomes,
        agent_performance=performance,
    )

    evaluator.evaluate(
        prediction=prediction,
        current_price_usd=180.5,
    )

    technical = performance.get("Technical Analyst")

    assert technical is not None
    assert technical.predictions == 1
    assert technical.action_predictions.get("HOLD", 0) == 0
