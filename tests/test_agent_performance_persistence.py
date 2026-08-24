import json
from datetime import datetime

import pytest

from atlas.trading.agent_performance_tracker import (
    AgentPerformanceTracker,
)
from atlas.trading.prediction_record import PredictionRecord


def test_tracker_persists_performance(tmp_path):

    path = tmp_path / "agent_performance.json"

    tracker = AgentPerformanceTracker(
        storage_path=path
    )

    tracker.record(
        analyst="Technical Analyst",
        correct=True,
    )

    tracker.record(
        analyst="Technical Analyst",
        correct=False,
    )

    assert path.exists()

    saved = json.loads(
        path.read_text()
    )

    assert saved["Technical Analyst"]["predictions"] == 2
    assert saved["Technical Analyst"]["correct"] == 1


def test_tracker_loads_existing_performance(tmp_path):

    path = tmp_path / "agent_performance.json"

    path.write_text(
        json.dumps(
            {
                "Technical Analyst": {
                    "predictions": 10,
                    "correct": 7,
                },
                "News Analyst": {
                    "predictions": 20,
                    "correct": 15,
                },
            }
        )
    )

    tracker = AgentPerformanceTracker(
        storage_path=path
    )

    technical = tracker.get(
        "Technical Analyst"
    )

    news = tracker.get(
        "News Analyst"
    )

    assert technical.predictions == 10
    assert technical.correct == 7
    assert technical.accuracy == 70.0

    assert news.predictions == 20
    assert news.correct == 15
    assert news.accuracy == 75.0


def test_tracker_clear_persists_empty_state(tmp_path):

    path = tmp_path / "agent_performance.json"

    tracker = AgentPerformanceTracker(
        storage_path=path
    )

    tracker.record(
        analyst="Technical Analyst",
        correct=True,
    )

    tracker.clear()

    assert tracker.history() == []

    saved = json.loads(
        path.read_text()
    )

    assert saved == {}


def test_tracker_without_storage_is_in_memory():

    tracker = AgentPerformanceTracker()

    tracker.record(
        analyst="Technical Analyst",
        correct=True,
    )

    assert tracker.count() == 1


def test_failed_atomic_replace_preserves_existing_json(
    monkeypatch,
    tmp_path,
):
    path = tmp_path / "agent_performance.json"
    tracker = AgentPerformanceTracker(
        storage_path=path
    )

    tracker.record(
        analyst="Technical Analyst",
        correct=True,
    )

    original_content = path.read_text()

    def fail_replace(*args, **kwargs):
        raise OSError("Atomic replacement failed.")

    monkeypatch.setattr(
        "atlas.trading.agent_performance_tracker.os.replace",
        fail_replace,
    )

    with pytest.raises(
        OSError,
        match="Atomic replacement failed.",
    ):
        tracker.record(
            analyst="Technical Analyst",
            correct=False,
        )

    assert path.read_text() == original_content
    assert list(
        tmp_path.glob(".agent_performance.json.*.tmp")
    ) == []


def test_rebuild_replaces_performance_from_evaluated_predictions(
    tmp_path,
):
    path = tmp_path / "agent_performance.json"
    tracker = AgentPerformanceTracker(
        storage_path=path
    )

    tracker.record(
        analyst="Stale Analyst",
        correct=True,
    )

    predictions = [
        PredictionRecord(
            symbol="NVDA",
            action="BUY",
            confidence=90.0,
            evidence=90.0,
            price_usd=100.0,
            timestamp=datetime.now(),
            analysts=["Technical Analyst", "News Analyst"],
            evaluated=True,
            correct=True,
        ),
        PredictionRecord(
            symbol="NVDA",
            action="SELL",
            confidence=80.0,
            evidence=80.0,
            price_usd=100.0,
            timestamp=datetime.now(),
            analysts=["Technical Analyst", "News Analyst"],
            evaluated=True,
            correct=False,
        ),
    ]

    tracker.rebuild_from_predictions(predictions)

    technical = tracker.get("Technical Analyst")
    news = tracker.get("News Analyst")

    assert tracker.get("Stale Analyst") is None
    assert technical.predictions == 2
    assert technical.correct == 1
    assert news.predictions == 2
    assert news.correct == 1
    assert json.loads(path.read_text()) == {
        "Technical Analyst": {
            "predictions": 2,
            "correct": 1,
        },
        "News Analyst": {
            "predictions": 2,
            "correct": 1,
        },
    }
