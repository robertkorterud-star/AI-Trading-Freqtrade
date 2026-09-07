from datetime import datetime

from atlas.trading.agent_performance_tracker import AgentPerformanceTracker
from atlas.trading.prediction_record import PredictionRecord


def test_rebuild_from_empty_predictions_clears_stale_performance():
    tracker = AgentPerformanceTracker()
    tracker.record(
        analyst="Technical Analyst",
        correct=True,
        action="BUY",
    )

    prediction = PredictionRecord(
        symbol="BTC-USD",
        action="BUY",
        confidence=90.0,
        evidence=90.0,
        price_usd=65000.0,
        timestamp=datetime.now(),
        analysts=["Technical Analyst"],
        evaluated=True,
        correct=True,
    )
    tracker.rebuild_from_predictions([prediction])
    assert tracker.count() == 1

    tracker.rebuild_from_predictions([])

    assert tracker.count() == 0
    assert tracker.history() == []
