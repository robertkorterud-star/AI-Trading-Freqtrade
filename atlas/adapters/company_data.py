"""
Company Data Adapter

Fetches company fundamental data.
"""

from dataclasses import dataclass

import yfinance as yf


@dataclass
class CompanyData:
    symbol: str
    name: str
    sector: str
    industry: str
    market_cap: float
    revenue_growth: float
    profit_margin: float
    debt_to_equity: float
    free_cash_flow: float
    employees: int


class CompanyDataAdapter:
    """Fetches company fundamental data."""

    def get(self, symbol: str) -> CompanyData:
        ticker = yf.Ticker(symbol)

        try:
            info = ticker.info
        except Exception:
            info = {}

        return CompanyData(
            symbol=symbol,
            name=info.get("longName", symbol),
            sector=info.get("sector", "Unknown"),
            industry=info.get("industry", "Unknown"),
            market_cap=float(info.get("marketCap") or 0),
            revenue_growth=float(info.get("revenueGrowth") or 0),
            profit_margin=float(info.get("profitMargins") or 0),
            debt_to_equity=float(info.get("debtToEquity") or 0),
            free_cash_flow=float(info.get("freeCashflow") or 0),
            employees=int(info.get("fullTimeEmployees") or 0),
        )
