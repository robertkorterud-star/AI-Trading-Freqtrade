"""
News Analyst

Simple implementation used for testing the ATLAS architecture.
"""

from atlas.agents.base_agent import BaseAgent
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult


class NewsAnalyst(BaseAgent):
    """Analyzes market news."""

    def __init__(self) -> None:
        super().__init__("News Analyst")

    def analyze(self, symbol: str) -> AnalysisResult:
        """Return a simulated news analysis."""

        return AnalysisResult(
            analyst=self.name,
            symbol=symbol,
            action=Action.BUY,
            confidence=91.0,
            evidence=88.0,
            reasoning=[
                "Positive market sentiment.",
                "No negative news detected.",
            ],
        )