"""Coordinate approved ATLAS decisions with the execution boundary."""

from atlas.execution.models import ExecutionRequest, ExecutionResult
from atlas.execution.protocol import ExecutionEngine
from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult


class DecisionExecutionService:
    """Translate an approved decision into an execution request.

    DecisionEngine remains responsible for deciding. Risk and portfolio
    assessments remain responsible for approval and capital constraints.
    This service only bridges an approved decision to execution.
    """

    def __init__(self, execution_engine: ExecutionEngine) -> None:
        self.execution_engine = execution_engine

    def execute(
        self,
        decision: DecisionResult,
        *,
        price: float | None = None,
        analysis_snapshot_id: int | None = None,
    ) -> ExecutionResult | None:
        """Execute an approved directional decision through the adapter.

        HOLD and WATCH decisions produce no execution request. Directional
        decisions require an allowed risk assessment with a positive position
        size. When a portfolio assessment is present, it must also be allowed,
        preventing a portfolio veto from being bypassed at execution.

        ``analysis_snapshot_id`` links a resulting paper trade back to the
        exact canonical ATLAS analysis snapshot that produced the decision.
        """
        if decision.action in {Action.HOLD, Action.WATCH}:
            return None

        risk = decision.risk_assessment
        if risk is None:
            raise ValueError("directional execution requires a risk assessment")
        if not risk.allowed:
            raise ValueError("directional execution requires an allowed risk assessment")
        if risk.action is not decision.action:
            raise ValueError("risk assessment action does not match decision action")
        if risk.position_size <= 0:
            raise ValueError("approved execution requires a positive position size")

        portfolio = decision.portfolio_assessment
        if portfolio is not None and not portfolio.allowed:
            raise ValueError("directional execution requires an allowed portfolio assessment")

        request = ExecutionRequest(
            symbol=decision.symbol,
            action=decision.action,
            quantity=risk.position_size,
            price=price,
            analysis_snapshot_id=analysis_snapshot_id,
        )
        return self.execution_engine.execute(request)
