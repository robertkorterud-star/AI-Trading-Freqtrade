from atlas.execution.service import DecisionExecutionService
from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult
from atlas.portfolio.manager import PortfolioAssessment
from atlas.risk.manager import RiskAssessment


class RecordingExecutionEngine:
    def __init__(self):
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return request


def decision_with_portfolio(*, portfolio_allowed: bool) -> DecisionResult:
    risk = RiskAssessment(
        action=Action.BUY,
        allowed=True,
        risk_level="LOW",
        position_size=0.1,
        position_value=10_000.0,
        stop_loss_price=98_000.0,
        take_profit_price=104_000.0,
        reasons=("Risk approved.",),
    )
    portfolio = PortfolioAssessment(
        allowed=portfolio_allowed,
        requested_value=10_000.0,
        approved_value=10_000.0 if portfolio_allowed else 0.0,
        current_exposure_value=0.0,
        resulting_exposure_value=10_000.0 if portfolio_allowed else 0.0,
        current_exposure_pct=0.0,
        resulting_exposure_pct=10.0 if portfolio_allowed else 0.0,
        available_capacity_value=10_000.0 if portfolio_allowed else 0.0,
        reasons=(
            "Portfolio allocation approved."
            if portfolio_allowed
            else "Portfolio allocation blocked.",
        ),
    )
    return DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=100.0,
        evidence=100.0,
        analysts=["Technical Analyst"],
        reasoning=["BUY"],
        risk_assessment=risk,
        portfolio_assessment=portfolio,
    )


def test_execution_uses_risk_size_when_portfolio_allocation_is_approved():
    recorder = RecordingExecutionEngine()
    service = DecisionExecutionService(recorder)

    result = service.execute(
        decision_with_portfolio(portfolio_allowed=True),
        price=100_000.0,
    )

    assert result is recorder.requests[0]
    assert result.quantity == 0.1


def test_execution_rejects_portfolio_blocked_decision():
    recorder = RecordingExecutionEngine()
    service = DecisionExecutionService(recorder)

    try:
        service.execute(
            decision_with_portfolio(portfolio_allowed=False),
            price=100_000.0,
        )
    except ValueError as exc:
        assert "portfolio" in str(exc).lower()
    else:
        raise AssertionError("blocked portfolio allocation must not reach execution")

    assert recorder.requests == []
