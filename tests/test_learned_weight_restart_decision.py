from datetime import datetime

from atlas.algorithms.decision_core import (
    DecisionAction,
    DecisionCore,
)
from atlas.algorithms.base import Action
from atlas.trading.agent_performance_tracker import (
    AgentPerformanceTracker,
)
from atlas.trading.agent_weight_engine import (
    AgentWeightEngine,
)
from atlas.trading.prediction_record import PredictionRecord


class Signal:
    def __init__(self, algorithm, action, confidence=1.0):
        self.algorithm = algorithm
        self.action = action
        self.confidence = confidence


def test_learned_weights_survive_restart_and_affect_decision(
    tmp_path,
):
    storage = tmp_path / "agent_performance.json"

    predictions = []

    for _ in range(20):
        predictions.append(
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
            )
        )

    for _ in range(20):
        predictions.append(
            PredictionRecord(
                symbol="BTC-USD",
                action="BUY",
                confidence=90.0,
                evidence=90.0,
                price_usd=65000.0,
                timestamp=datetime.now(),
                analysts=["News Analyst"],
                evaluated=True,
                correct=False,
            )
        )

    tracker = AgentPerformanceTracker(
        storage_path=storage,
    )

    tracker.rebuild_from_predictions(predictions)

    # Simulate an ATLAS restart.
    restarted_tracker = AgentPerformanceTracker(
        storage_path=storage,
    )

    engine = AgentWeightEngine(
        restarted_tracker,
    )

    weights = engine.calculate(
        action="BUY",
    )

    assert (
        weights["Technical Analyst"]
        > weights["News Analyst"]
    )

    core = DecisionCore(
        agent_weight_engine=engine,
    )

    result = core.decide(
        signals=[
            Signal(
                "agent:Technical Analyst",
                Action.BUY,
            ),
            Signal(
                "agent:News Analyst",
                Action.BUY,
            ),
        ],
    )

    assert result.action == DecisionAction.BUY
    assert result.confidence > 0.0
    assert result.score > 0.0
