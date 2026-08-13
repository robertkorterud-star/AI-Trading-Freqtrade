from unittest.mock import patch

from atlas.adapters.company_data import CompanyDataAdapter


def test_company_data_adapter_returns_company_data():
    fake_info = {
        "longName": "NVIDIA Corporation",
        "sector": "Technology",
        "industry": "Semiconductors",
        "marketCap": 1000000000000,
        "revenueGrowth": 0.25,
        "profitMargins": 0.55,
        "debtToEquity": 20.0,
        "freeCashflow": 50000000000,
        "fullTimeEmployees": 36000,
    }

    with patch("atlas.adapters.company_data.yf.Ticker") as mock_ticker:
        mock_ticker.return_value.info = fake_info

        data = CompanyDataAdapter().get("NVDA")

    assert data.symbol == "NVDA"
    assert data.name == "NVIDIA Corporation"
    assert data.sector == "Technology"
    assert data.industry == "Semiconductors"
    assert data.market_cap == 1000000000000
    assert data.revenue_growth == 0.25
    assert data.profit_margin == 0.55
    assert data.debt_to_equity == 20.0
    assert data.free_cash_flow == 50000000000
    assert data.employees == 36000


def test_company_data_adapter_handles_missing_values():
    fake_info = {
        "longName": "Test Company",
    }

    with patch("atlas.adapters.company_data.yf.Ticker") as mock_ticker:
        mock_ticker.return_value.info = fake_info

        data = CompanyDataAdapter().get("TEST")

    assert data.symbol == "TEST"
    assert data.name == "Test Company"
    assert data.market_cap == 0
    assert data.revenue_growth == 0
    assert data.profit_margin == 0
    assert data.debt_to_equity == 0
    assert data.free_cash_flow == 0
    assert data.employees == 0
