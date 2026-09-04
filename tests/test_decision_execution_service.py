import pytest

from atlas.execution import (
    DecisionExecutionService,
    DryRunExecutionAdapter,
    ExecutionEngine,
    ExecutionStatus,
)
from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult
from atlas.risk.manager import RiskAssessment


def approved_decision(action: Action = Action.BUY) -> DecisionResult:
    return DecisionResult(
        symbol="BTC/USDT",
        action=action,
        confidence=90.0,
        evidence=90.0,
        risk_assessment=RiskAssessment(
            action=action,
            allowed=True,
            risk_level="LOW",
            position_size=0.25,
            position_value=25_000.0,
            stop_loss_price=98_000.0,
            take_profit_price=104_000.0,
            reasons=("approved",),
        ),
    )


def test_approved_decision_is_translated_to_dryrun_execution() -> None:
    adapter = DryRunExecutionAdapter()
    service = DecisionExecutionService(ExecutionEngine(adapter))

    result = service.execute(approved_decision(), price=100_000.0)

    assert result is not None
    assert result.status is ExecutionStatus.SIMULATED
    assert adapter.requests[0].symbol == "BTC/USDT"
    assert adapter.requests[0].action is Action.BUY
    assert adapter.requests[0].quantity == 0.25
    assert adapter.requests[0].price == 100_000.0


def test_hold_decision_does_not_create_execution_request() -> None:
    adapter = DryRunExecutionAdapter()
    service = DecisionExecutionService(ExecutionEngine(adapter))

    result = service.execute(DecisionResult(
        symbol="BTC/USDT",
        action=Action.HOLD,
        confidence=50.0,
        evidence=50.0,
    ))

    assert result is None
    assert adapter.requests == []


def test_directional_decision_requires_risk_assessment() -> None:
    service = DecisionExecutionService(ExecutionEngine(DryRunExecutionAdapter()))

    with pytest.raises(ValueError, match="risk assessment"):
        service.execute(DecisionResult(
            symbol="BTC/USDT",
            action=Action.BUY,
            confidence=90.0,
            evidence=90.0,
        ))


def test_blocked_risk_cannot_reach_execution() -> None:
    adapter = DryRunExecutionAdapter()
    service = DecisionExecutionService(ExecutionEngine(adapter))
    decision = approved_decision()
    decision.risk_assessment = RiskAssessment(
        action=Action.BUY,
        allowed=False,
        risk_level="BLOCKED",
        position_size=0.0,
        position_value=0.0,
        stop_loss_price=None,
        take_profit_price=None,
        reasons=("blocked",),
    )

    with pytest.raises(ValueError, match="allowed risk assessment"):
        service.execute(decision)

    assert adapter.requests == []
