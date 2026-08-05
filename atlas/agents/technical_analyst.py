"""
Technical Analyst
"""

from atlas.agents.base_agent import BaseAgent

from atlas.adapters.market_data import MarketDataAdapter

from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult


class TechnicalAnalyst(BaseAgent):
    """Technical trend analyst using moving averages."""

    def __init__(self):

        super().__init__("Technical Analyst")

        self.market = MarketDataAdapter()

    def analyze(self, symbol: str) -> AnalysisResult:

        data = self.market.get(symbol)

        if data.price > data.ma20 > data.ma50:

            action = Action.BUY

            confidence = 88

            evidence = 85

            reasoning = [

                "Price is above MA20.",

                "MA20 is above MA50.",

                "Overall trend is bullish.",

            ]

        elif data.price < data.ma20 < data.ma50:

            action = Action.SELL

            confidence = 88

            evidence = 85

            reasoning = [

                "Price is below MA20.",

                "MA20 is below MA50.",

                "Overall trend is bearish.",

            ]

        else:

            action = Action.HOLD

            confidence = 65

            evidence = 65

            reasoning = [

                "Mixed market trend.",

                "Waiting for confirmation.",

            ]

        return AnalysisResult(

            analyst=self.name,

            symbol=data.symbol,

            action=action,

            confidence=confidence,

            evidence=evidence,

            reasoning=reasoning,

        )