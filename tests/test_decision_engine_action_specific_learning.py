from atlas.decision.engine import DecisionEngine
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult


class ActionAwareWeightEngine:
    def calculate(self, action=None):
        if action == Action.BUY.value:
            return {
                "Technical Analyst": 0.60,
                "News Analyst": 0.40,
            }
        if action == Action.SELL.value:
            return {
                "Technical Analyst": 0.20,
                "News Analyst": 0.80,
            }
        return {
            "Technical Analyst": 0.50,
            "News Analyst": 0.50,
        }


def _conflicting_results():
    return [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Technical Analyst",
            action=Action.BUY,
            confidence=90.0,
            evidence=90.0,
            reasoning=["Technical BUY."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="News Analyst",
            action=Action.SELL,
            confidence=90.0,
            evidence=90.0,
            reasoning=["News SELL."],
        ),
    ]


def test_canonical_decision_engine_uses_action_specific_learned_support():
    engine = DecisionEngine()
    engine.agent_weight_engine = ActionAwareWeightEngine()

    decision = engine.evaluate(_conflicting_results())

    assert decision.action_support_analyst == "News Analyst"
    assert decision.action_support_action == Action.SELL
    assert decision.action_support_weight == 0.80
    assert any(
        "News Analyst supports SELL with 80.0% learned weight" in reason
        for reason in decision.reasoning
    )


def test_action_specific_support_does_not_replace_canonical_generic_weights():
    engine = DecisionEngine()
    engine.agent_weight_engine = ActionAwareWeightEngine()

    decision = engine.evaluate(_conflicting_results())

    assert decision.agent_weights == {
        "Technical Analyst": 0.50,
        "News Analyst": 0.50,
    }
