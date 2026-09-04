from atlas.decision.engine import DecisionEngine
from atlas.execution.service import DecisionExecutionService
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult
from atlas.portfolio.manager import PortfolioManager, PortfolioPosition
from atlas.risk.manager import RiskManager


class RecordingExecutionEngine:
    def __init__(self):
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return request


def buy_result():
    return AnalysisResult(
        symbol="BTC-USD",
        analyst="Technical Analyst",
        action=Action.BUY,
        confidence=100.0,
        evidence=100.0,
        reasoning=["Strong BUY signal."],
    )


def test_decision_engine_attaches_allowed_risk_assessment():
    engine = DecisionEngine(risk_manager=RiskManager())

    decision = engine.evaluate(
        [buy_result()],
        price=100_000.0,
        equity=100_000.0,
    )

    assert decision.action == Action.BUY
    assert decision.risk_assessment is not None
    assert decision.risk_assessment.allowed is True
    assert decision.risk_assessment.action is Action.BUY
    assert decision.risk_assessment.position_size > 0
    assert decision.risk_assessment.position_value > 0


def test_decision_engine_blocks_direction_when_drawdown_limit_is_reached():
    engine = DecisionEngine(
        risk_manager=RiskManager(max_drawdown_pct=20.0),
    )

    decision = engine.evaluate(
        [buy_result()],
        price=100_000.0,
        equity=100_000.0,
        drawdown_pct=20.0,
    )

    assert decision.action is Action.HOLD
    assert decision.risk_assessment is not None
    assert decision.risk_assessment.allowed is False
    assert decision.risk_assessment.action is Action.BUY
    assert decision.risk_assessment.position_size == 0.0
    assert any("drawdown" in reason.lower() for reason in decision.risk_assessment.reasons)


def test_decision_engine_blocks_buy_when_portfolio_has_no_capacity():
    engine = DecisionEngine(
        risk_manager=RiskManager(),
        portfolio_manager=PortfolioManager(
            max_exposure_pct=100.0,
            max_single_position_pct=20.0,
        ),
    )

    decision = engine.evaluate(
        [buy_result()],
        price=100_000.0,
        equity=100_000.0,
        portfolio_positions=[
            PortfolioPosition(symbol="ETH-USD", market_value=100_000.0),
        ],
    )

    assert decision.action is Action.HOLD
    assert decision.risk_assessment is not None
    assert decision.risk_assessment.allowed is True
    assert decision.portfolio_assessment is not None
    assert decision.portfolio_assessment.allowed is False
    assert decision.portfolio_assessment.approved_value == 0.0


def test_execution_service_requires_allowed_matching_risk_assessment():
    engine = DecisionEngine(risk_manager=RiskManager())
    decision = engine.evaluate(
        [buy_result()],
        price=100_000.0,
        equity=100_000.0,
    )
    recorder = RecordingExecutionEngine()
    service = DecisionExecutionService(recorder)

    result = service.execute(decision, price=100_000.0)

    assert result is recorder.requests[0]
    assert result.symbol == "BTC-USD"
    assert result.action is Action.BUY
    assert result.quantity == decision.risk_assessment.position_size


def test_execution_service_does_not_execute_blocked_decision():
    engine = DecisionEngine(
        risk_manager=RiskManager(max_drawdown_pct=20.0),
    )
    decision = engine.evaluate(
        [buy_result()],
        price=100_000.0,
        equity=100_000.0,
        drawdown_pct=20.0,
    )
    recorder = RecordingExecutionEngine()
    service = DecisionExecutionService(recorder)

    result = service.execute(decision, price=100_000.0)

    assert result is None
    assert recorder.requests == []
