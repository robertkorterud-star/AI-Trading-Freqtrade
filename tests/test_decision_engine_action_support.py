from atlas.decision.engine import DecisionEngine
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult


class ActionAwareWeightEngine:

    def calculate(self, action=None):
        if action == "BUY":
            return {
                "Technical Analyst": 0.60,
                "News Analyst": 0.25,
                "Company Analyst": 0.15,
            }

        if action == "SELL":
            return {
                "Technical Analyst": 0.20,
                "News Analyst": 0.60,
                "Company Analyst": 0.20,
            }

        return {
            "Technical Analyst": 0.40,
            "News Analyst": 0.35,
            "Company Analyst": 0.25,
        }


def make_results():
    return [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Technical Analyst",
            action=Action.BUY,
            confidence=90.0,
            evidence=90.0,
            reasoning=["Strong technical BUY."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="News Analyst",
            action=Action.SELL,
            confidence=80.0,
            evidence=80.0,
            reasoning=["Negative news."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Company Analyst",
            action=Action.HOLD,
            confidence=70.0,
            evidence=70.0,
            reasoning=["Neutral fundamentals."],
        ),
    ]


def test_decision_engine_reports_strongest_buy_support():
    engine = DecisionEngine()
    engine.agent_weight_engine = ActionAwareWeightEngine()

    decision = engine.evaluate(make_results())

    assert decision.action_support_analyst == "Technical Analyst"
    assert decision.action_support_action == Action.BUY
    assert decision.action_support_weight == 0.60


def test_decision_engine_reports_strongest_directional_support():
    engine = DecisionEngine()
    engine.agent_weight_engine = ActionAwareWeightEngine()

    decision = engine.evaluate(make_results())

    assert decision.action_support_analyst in {
        "Technical Analyst",
        "News Analyst",
    }

    assert decision.action_support_action in {
        Action.BUY,
        Action.SELL,
    }

    assert decision.action_support_weight == 0.60


def test_decision_engine_preserves_action_specific_weights():
    engine = DecisionEngine()
    engine.agent_weight_engine = ActionAwareWeightEngine()

    decision = engine.evaluate(make_results())

    assert decision.agent_weights == {
        "Technical Analyst": 0.40,
        "News Analyst": 0.35,
        "Company Analyst": 0.25,
    }


def test_decision_engine_handles_missing_weight_engine():
    engine = DecisionEngine()

    decision = engine.evaluate(make_results())

    assert decision.action_support_analyst is None
    assert decision.action_support_action is None
    assert decision.action_support_weight == 0.0


def test_decision_engine_explains_learned_action_support():
    engine = DecisionEngine()
    engine.agent_weight_engine = ActionAwareWeightEngine()

    decision = engine.evaluate(make_results())

    assert any(
        "Learned support:" in reason
        for reason in decision.reasoning
    )

    assert any(
        "Technical Analyst supports BUY with 60.0% learned weight."
        in reason
        for reason in decision.reasoning
    )
