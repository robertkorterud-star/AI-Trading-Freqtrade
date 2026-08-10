from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult
from atlas.risk.risk_engine import RiskEngine


def test_risk_engine_approves_buy_at_20_percent():

    risk = RiskEngine()

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=89.5,
        evidence=86.5,
    )

    result = risk.evaluate(
        decision=decision,
        total_equity_nok=5000,
        cash_nok=5000,
        requested_amount_nok=1000,
    )

    assert result.approved is True
    assert result.max_position_nok == 1000.0


def test_risk_engine_rejects_buy_above_20_percent():

    risk = RiskEngine()

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=89.5,
        evidence=86.5,
    )

    result = risk.evaluate(
        decision=decision,
        total_equity_nok=5000,
        cash_nok=5000,
        requested_amount_nok=1200,
    )

    assert result.approved is False


def test_risk_engine_rejects_sell_without_position():

    risk = RiskEngine()

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.SELL,
        confidence=40.0,
        evidence=40.0,
    )

    result = risk.evaluate(
        decision=decision,
        total_equity_nok=5000,
        cash_nok=5000,
        requested_amount_nok=0,
        position_exists=False,
    )

    assert result.approved is False


def test_risk_engine_approves_sell_with_position():

    risk = RiskEngine()

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.SELL,
        confidence=40.0,
        evidence=40.0,
    )

    result = risk.evaluate(
        decision=decision,
        total_equity_nok=5000,
        cash_nok=4000,
        requested_amount_nok=1000,
        position_exists=True,
    )

    assert result.approved is True
