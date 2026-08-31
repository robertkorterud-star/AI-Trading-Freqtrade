from atlas.algorithms.decision_core import DecisionAction, DecisionCore
from atlas.algorithms.base import Action
from atlas.trading.agent_performance_tracker import AgentPerformanceTracker
from atlas.trading.agent_weight_engine import AgentWeightEngine


class Signal:
    def __init__(self, algorithm, action, confidence=1.0):
        self.algorithm = algorithm
        self.action = action
        self.confidence = confidence


def test_learned_weights_affect_real_decision_flow():
    tracker = AgentPerformanceTracker()

    for _ in range(20):
        tracker.record("Technical Analyst", True, action="BUY")

    for _ in range(20):
        tracker.record("News Analyst", False, action="BUY")

    engine = AgentWeightEngine(tracker)

    weights = engine.calculate(action="BUY")

    assert weights["Technical Analyst"] > weights["News Analyst"]

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
