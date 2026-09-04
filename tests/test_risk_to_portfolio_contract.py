from atlas.models.action import Action
from atlas.portfolio.manager import PortfolioManager, PortfolioPosition
from atlas.risk.manager import RiskManager



def test_risk_approved_position_value_is_the_portfolio_allocation_request():
    risk = RiskManager()
    portfolio = PortfolioManager()

    assessment = risk.assess(
        action=Action.BUY,
        price=100_000.0,
        equity=100_000.0,
    )
    allocation = portfolio.assess(
        symbol="BTC-USD",
        requested_value=assessment.position_value,
        equity=100_000.0,
    )

    assert assessment.allowed is True
    assert assessment.position_value > 0
    assert allocation.requested_value == round(assessment.position_value, 2)
    assert allocation.approved_value == round(assessment.position_value, 2)
    assert allocation.allowed is True


def test_portfolio_can_veto_a_risk_approved_allocation():
    risk = RiskManager()
    portfolio = PortfolioManager(max_exposure_pct=100.0, max_single_position_pct=20.0)

    assessment = risk.assess(
        action=Action.BUY,
        price=100_000.0,
        equity=100_000.0,
    )
    allocation = portfolio.assess(
        symbol="BTC-USD",
        requested_value=assessment.position_value,
        equity=100_000.0,
        positions=[
            PortfolioPosition(symbol="ETH-USD", market_value=100_000.0),
        ],
    )

    assert assessment.allowed is True
    assert assessment.position_value > 0
    assert allocation.allowed is False
    assert allocation.approved_value == 0.0
    assert allocation.requested_value == round(assessment.position_value, 2)
    assert any("exposure capacity" in reason.lower() for reason in allocation.reasons)
