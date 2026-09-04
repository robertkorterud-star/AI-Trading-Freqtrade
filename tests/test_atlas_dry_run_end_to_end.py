from atlas.decision.engine import DecisionEngine
from atlas.execution.dryrun import DryRunExecutionAdapter
from atlas.execution.protocol import ExecutionEngine
from atlas.execution.service import DecisionExecutionService
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult
from atlas.portfolio.manager import PortfolioManager
from atlas.risk.manager import RiskManager


def buy_result() -> AnalysisResult:
    return AnalysisResult(
        symbol="BTC-USD",
        analyst="Technical Analyst",
        action=Action.BUY,
        confidence=100.0,
        evidence=100.0,
        reasoning=["Strong BUY signal."],
    )


def test_modern_atlas_dry_run_chain_executes_only_risk_approved_size():
    """Lock the modern decision -> risk -> portfolio -> dry-run path."""
    decision_engine = DecisionEngine(
        risk_manager=RiskManager(),
        portfolio_manager=PortfolioManager(),
    )
    decision = decision_engine.evaluate(
        [buy_result()],
        price=100_000.0,
        equity=100_000.0,
    )

    assert decision.action is Action.BUY
    assert decision.risk_assessment is not None
    assert decision.risk_assessment.allowed is True
    assert decision.portfolio_assessment is not None
    assert decision.portfolio_assessment.allowed is True

    adapter = DryRunExecutionAdapter()
    service = DecisionExecutionService(ExecutionEngine(adapter))
    result = service.execute(decision, price=100_000.0)

    assert result is not None
    assert result.status.value == "SIMULATED"
    assert result.symbol == decision.symbol
    assert result.action is Action.BUY
    assert result.quantity == decision.risk_assessment.position_size
    assert len(adapter.requests) == 1
    assert adapter.requests[0].quantity == decision.risk_assessment.position_size
