"""
Company Analyst

Analyzes company fundamentals.
"""

from atlas.agents.base_agent import BaseAgent
from atlas.adapters.company_data import CompanyDataAdapter
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult


class CompanyAnalyst(BaseAgent):
    """Analyzes company fundamentals."""

    def __init__(self, config=None) -> None:
        super().__init__("Company Analyst", config=config)
        self.company = CompanyDataAdapter()

    def analyze(self, symbol: str) -> AnalysisResult:
        """Analyze company fundamentals."""

        data = self.company.get(symbol)

        score = 0
        reasoning = []

        # Revenue growth
        if data.revenue_growth >= 0.15:
            score += 1
            reasoning.append(
                self.t("strong_revenue_growth")
            )
        elif data.revenue_growth > 0:
            score += 0.5
            reasoning.append(
                self.t("revenue_growing")
            )
        else:
            reasoning.append(
                self.t("revenue_growth_weak")
            )

        # Profitability
        if data.profit_margin >= 0.20:
            score += 1
            reasoning.append(
                self.t("strong_profit_margin")
            )
        elif data.profit_margin > 0:
            score += 0.5
            reasoning.append(
                self.t("company_profitable")
            )
        else:
            reasoning.append(
                self.t("profitability_weak")
            )

        # Debt
        if data.debt_to_equity == 0:
            reasoning.append(
                self.t("no_debt_data")
            )
        elif data.debt_to_equity <= 100:
            score += 1
            reasoning.append(
                self.t("debt_manageable")
            )
        else:
            reasoning.append(
                self.t("debt_high")
            )

        # Free cash flow
        if data.free_cash_flow > 0:
            score += 1
            reasoning.append(
                self.t("positive_free_cash_flow")
            )
        else:
            reasoning.append(
                self.t("free_cash_flow_weak")
            )

        # Determine action
        if score >= 3:
            action = Action.BUY
            confidence = 85.0
        elif score >= 2:
            action = Action.HOLD
            confidence = 70.0
        else:
            action = Action.SELL
            confidence = 60.0

        evidence = min(95.0, 55.0 + (score * 10.0))

        return AnalysisResult(
            analyst=self.name,
            symbol=data.symbol,
            action=action,
            confidence=confidence,
            evidence=evidence,
            reasoning=reasoning,
        )
