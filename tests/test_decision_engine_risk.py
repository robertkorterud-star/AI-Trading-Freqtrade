import pytest

from atlas.decision.engine import DecisionEngine
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult
from atlas.risk.manager import RiskManager


def _buy_result() -> AnalysisResult:
    return AnalysisResult(
        analyst="technical",
        symbol="EQNR.OL",
        action=Action.BUY,
        confidence=90.0,
        evidence=90.0,
        reasoning=["Strong bullish trend."],
    )


def test_decision_engine_applies_risk_without_changing_allowed_direction():
    engine = DecisionEngine(risk_manager=RiskManager())

    result = engine.evaluate(
        [_buy_result()],
        price=100.0,
        equity=10_000.0,
    )

    assert result.action is Action.BUY
    assert result.risk_assessment is not None
    assert result.risk_assessment.allowed is True
    assert result.risk_assessment.position_value > 0.0
    assert result.risk_assessment.stop_loss_price == pytest.approx(98.0)
    assert result.risk_assessment.take_profit_price == pytest.approx(104.0)


def test_decision_engine_blocks_direction_when_risk_limit_is_reached():
    engine = DecisionEngine(risk_manager=RiskManager(max_drawdown_pct=10.0))

    result = engine.evaluate(
        [_buy_result()],
        price=100.0,
        equity=10_000.0,
        drawdown_pct=10.0,
    )

    assert result.action is Action.HOLD
    assert result.risk_assessment is not None
    assert result.risk_assessment.allowed is False
    assert result.risk_assessment.risk_level == "BLOCKED"
    assert any("Risk management blocked" in reason for reason in result.reasoning)


def test_risk_enabled_decision_requires_market_and_account_context():
    engine = DecisionEngine(risk_manager=RiskManager())

    with pytest.raises(ValueError, match="price and equity"):
        engine.evaluate([_buy_result()])
