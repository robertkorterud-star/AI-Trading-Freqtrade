"""
Technical Analyst
"""

from atlas.agents.base_agent import BaseAgent

from atlas.adapters.market_data import MarketDataAdapter

from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult


class TechnicalAnalyst(BaseAgent):
    """Technical trend analyst using moving averages."""

    def __init__(self, config=None):

        super().__init__("Technical Analyst", config=config)

        self.market = MarketDataAdapter()

    def analyze(self, symbol: str) -> AnalysisResult:

        data = self.market.get(symbol)

        if data.price > data.ma20 > data.ma50:

            action = Action.BUY

            confidence = 88

            evidence = 85

            reasoning = [

                self.t("price_above_ma20"),

                self.t("ma20_above_ma50"),

                self.t("overall_trend_bullish"),

            ]

        elif data.price < data.ma20 < data.ma50:

            action = Action.SELL

            confidence = 88

            evidence = 85

            reasoning = [

                self.t("price_below_ma20"),

                self.t("ma20_below_ma50"),

                self.t("overall_trend_bearish"),

            ]

        else:

            action = Action.HOLD

            confidence = 65

            evidence = 65

            reasoning = [

                self.t("mixed_market_trend"),

                self.t("waiting_confirmation"),

            ]

        return AnalysisResult(

            analyst=self.name,

            symbol=data.symbol,

            action=action,

            confidence=confidence,

            evidence=evidence,

            reasoning=reasoning,

        )
