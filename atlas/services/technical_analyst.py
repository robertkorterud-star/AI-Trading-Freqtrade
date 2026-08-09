"""
Technical Analyst
"""

from atlas.core.agent import BaseAgent
from atlas.models.analysis import AnalysisResult
from atlas.models.decision import Action

from atlas.services.technical_service import TechnicalService


class TechnicalAnalyst(BaseAgent):
    """Analyzes technical market data."""

    def __init__(self):

        self.service = TechnicalService()

    @property
    def name(self) -> str:
        return "Technical Analyst"

    def analyze(self, symbol: str) -> AnalysisResult:

        snapshot = self.service.get_snapshot(symbol)

        confidence = 50.0
        evidence = 50.0
        action = Action.HOLD
        reasoning = []

        if snapshot.trend == "Bullish":
            action = Action.BUY
            confidence = 82.0
            evidence = 76.0

            reasoning.extend(
                [
                    "Price is above MA20.",
                    "MA20 is above MA50.",
                    "Trend is bullish.",
                ]
            )

        elif snapshot.trend == "Bearish":
            action = Action.SELL
            confidence = 82.0
            evidence = 76.0

            reasoning.extend(
                [
                    "Price is below MA20.",
                    "MA20 is below MA50.",
                    "Trend is bearish.",
                ]
            )

        else:
            reasoning.append("Trend is neutral.")

        return AnalysisResult(
            analyst=self.name,
            symbol=symbol,
            action=action,
            confidence=confidence,
            evidence=evidence,
            reasoning=reasoning,
        )