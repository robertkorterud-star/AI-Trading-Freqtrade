"""
Technical Analyst
"""

from atlas.agents.base_agent import BaseAgent

from atlas.adapters.market_data import MarketDataAdapter
from atlas.intelligence.volume import (
    VolumeIntelligence,
    analyze_volume,
)

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

        # -------------------------------------------------
        # Volume Intelligence
        #
        # Volume remains explanatory only.
        # It does not change action, confidence or evidence.
        # -------------------------------------------------

        self.volume_intelligence = analyze_volume(
            volume=getattr(data, "volume", 0.0),
            average_volume=getattr(
                data,
                "average_volume",
                0.0,
            ),
            volume_ratio=getattr(
                data,
                "volume_ratio",
                None,
            ),
        )

        volume = self.volume_intelligence

        if volume.level != "UNKNOWN":

            reasoning.append(
                f"Volume level: {volume.level} "
                f"({volume.volume_ratio:.2f}x average volume)."
            )

            reasoning.append(
                volume.interpretation
            )

        return AnalysisResult(

            analyst=self.name,

            symbol=data.symbol,

            action=action,

            confidence=confidence,

            evidence=evidence,

            reasoning=reasoning,

        )
