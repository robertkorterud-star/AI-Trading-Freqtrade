from unittest.mock import patch

from atlas.agents.company_analyst import CompanyAnalyst
from atlas.models.action import Action
from atlas.adapters.company_data import CompanyData


def test_company_analyst_identifies_strong_company():
    data = CompanyData(
        symbol="NVDA",
        name="NVIDIA Corporation",
        sector="Technology",
        industry="Semiconductors",
        market_cap=1000000000000,
        revenue_growth=0.25,
        profit_margin=0.55,
        debt_to_equity=20.0,
        free_cash_flow=50000000000,
        employees=36000,
    )

    with patch(
        "atlas.agents.company_analyst.CompanyDataAdapter.get",
        return_value=data,
    ):
        result = CompanyAnalyst().analyze("NVDA")

    assert result.analyst == "Company Analyst"
    assert result.symbol == "NVDA"
    assert result.action == Action.BUY
    assert result.confidence == 85.0
    assert result.evidence == 95.0
    assert len(result.reasoning) >= 4


def test_company_analyst_identifies_weak_company():
    data = CompanyData(
        symbol="TEST",
        name="Test Company",
        sector="Unknown",
        industry="Unknown",
        market_cap=1000000,
        revenue_growth=-0.10,
        profit_margin=-0.05,
        debt_to_equity=250.0,
        free_cash_flow=-100000,
        employees=100,
    )

    with patch(
        "atlas.agents.company_analyst.CompanyDataAdapter.get",
        return_value=data,
    ):
        result = CompanyAnalyst().analyze("TEST")

    assert result.analyst == "Company Analyst"
    assert result.symbol == "TEST"
    assert result.action == Action.SELL
    assert result.confidence == 60.0
