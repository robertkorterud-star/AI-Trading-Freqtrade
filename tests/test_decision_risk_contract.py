from atlas.decision.engine import DecisionEngine
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult
from atlas.risk.manager import RiskManager


class RecordingRiskManager(RiskManager):
    def __init__(self):
        super().__init__()
        self.calls = []

    def assess(self, **kwargs):
        self.calls.append(kwargs)
        return super().assess(**kwargs)


def buy_result():
    return AnalysisResult(
        symbol="BTC-USD",
        analyst="Technical Analyst",
        action=Action.BUY,
        confidence=100.0,
        evidence=100.0,
        reasoning=["Strong BUY signal."],
    )


def test_decision_engine_passes_final_direction_and_risk_context_to_risk_manager():
    risk_manager = RecordingRiskManager()
    engine = DecisionEngine(risk_manager=risk_manager)

    decision = engine.evaluate(
        [buy_result()],
        price=100_000.0,
        equity=100_000.0,
        current_exposure_pct=10.0,
        drawdown_pct=5.0,
    )

    assert len(risk_manager.calls) == 1
    call = risk_manager.calls[0]
    assert call["action"] is Action.BUY
    assert call["price"] == 100_000.0
    assert call["equity"] == 100_000.0
    assert call["current_exposure_pct"] == 10.0
    assert call["drawdown_pct"] == 5.0
    assert decision.risk_assessment is not None
    assert decision.risk_assessment.action is Action.BUY


def test_decision_engine_requires_price_and_equity_before_risk_assessment():
    risk_manager = RecordingRiskManager()
    engine = DecisionEngine(risk_manager=risk_manager)

    try:
        engine.evaluate([buy_result()], price=100_000.0)
    except ValueError as exc:
        assert str(exc) == "price and equity are required when risk_manager is configured"
    else:
        raise AssertionError("DecisionEngine must require equity for risk assessment")

    assert risk_manager.calls == []
