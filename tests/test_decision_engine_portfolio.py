from atlas.decision.engine import DecisionEngine
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult
from atlas.portfolio.manager import PortfolioManager, PortfolioPosition
from atlas.risk.manager import RiskManager


def _buy_results():
    return [
        AnalysisResult(
            analyst="technical",
            symbol="EQNR.OL",
            action=Action.BUY,
            confidence=90.0,
            evidence=95.0,
        ),
        AnalysisResult(
            analyst="momentum",
            symbol="EQNR.OL",
            action=Action.BUY,
            confidence=90.0,
            evidence=95.0,
        ),
    ]


def test_portfolio_allocation_is_recorded_when_buy_is_allowed():
    engine = DecisionEngine(
        risk_manager=RiskManager(),
        portfolio_manager=PortfolioManager(),
    )

    result = engine.evaluate(
        _buy_results(),
        price=100.0,
        equity=100_000.0,
    )

    assert result.action is Action.BUY
    assert result.portfolio_assessment is not None
    assert result.portfolio_assessment.allowed is True
    assert result.portfolio_assessment.approved_value == 1_000.0
    assert engine.last_portfolio_assessment is result.portfolio_assessment


def test_portfolio_can_block_buy_after_risk_sizing():
    engine = DecisionEngine(
        risk_manager=RiskManager(
            risk_per_trade_pct=10.0,
            max_position_pct=60.0,
            max_exposure_pct=100.0,
        ),
        portfolio_manager=PortfolioManager(
            max_exposure_pct=50.0,
            max_single_position_pct=20.0,
        ),
    )

    result = engine.evaluate(
        _buy_results(),
        price=100.0,
        equity=100_000.0,
        portfolio_positions=(PortfolioPosition("OTHER.OL", 19_000.0),),
    )

    assert result.action is Action.HOLD
    assert result.risk_assessment is not None
    assert result.risk_assessment.allowed is True
    assert result.portfolio_assessment is not None
    assert result.portfolio_assessment.allowed is False
    assert any("exceeds" in reason for reason in result.portfolio_assessment.reasons)


def test_portfolio_manager_is_not_invoked_for_hold():
    class FailingPortfolioManager:
        def assess(self, **kwargs):
            raise AssertionError("portfolio assessment should not run for HOLD")

    results = [
        AnalysisResult(
            analyst="technical",
            symbol="EQNR.OL",
            action=Action.HOLD,
            confidence=60.0,
            evidence=60.0,
        ),
        AnalysisResult(
            analyst="momentum",
            symbol="EQNR.OL",
            action=Action.HOLD,
            confidence=60.0,
            evidence=60.0,
        ),
    ]

    result = DecisionEngine(portfolio_manager=FailingPortfolioManager()).evaluate(results)

    assert result.action is Action.HOLD
    assert result.portfolio_assessment is None
