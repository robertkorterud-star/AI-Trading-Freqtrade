from atlas.decision.engine import DecisionEngine
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult


class ActionAwareWeightEngine:
    def calculate(self, action=None):
        if action == Action.BUY.value:
            return {
                "Technical Analyst": 0.90,
                "News Analyst": 0.10,
            }
        if action == Action.SELL.value:
            return {
                "Technical Analyst": 0.10,
                "News Analyst": 0.90,
            }
        return {
            "Technical Analyst": 0.50,
            "News Analyst": 0.50,
        }


def test_action_specific_learned_weights_drive_canonical_direction():
    results = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Technical Analyst",
            action=Action.BUY,
            confidence=100.0,
            evidence=100.0,
            reasoning=["Technical BUY."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="News Analyst",
            action=Action.SELL,
            confidence=100.0,
            evidence=100.0,
            reasoning=["News SELL."],
        ),
    ]

    engine = DecisionEngine()
    engine.agent_weight_engine = ActionAwareWeightEngine()

    decision = engine.evaluate(results)

    assert decision.action == Action.BUY
    assert decision.dominant_action == Action.BUY
    assert decision.dominant_weight == 90.0
    assert decision.agent_weights == {
        "Technical Analyst": 0.90,
        "News Analyst": 0.10,
    }
    assert decision.evidence == 100.0
