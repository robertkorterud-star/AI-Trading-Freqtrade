"""
Technical Analyst
"""

from atlas.agents.base_agent import BaseAgent

from atlas.adapters.market_data import MarketDataAdapter
from atlas.intelligence.technical_signal import generate_technical_signal
from atlas.intelligence.volume import (
    VolumeIntelligence,
    analyze_volume,
)

from atlas.intelligence.volume_confirmation import (
    VolumeConfirmation,
    confirm_volume,
)

from atlas.models.analysis_result import AnalysisResult


class TechnicalAnalyst(BaseAgent):
    """Technical analyst backed by ATLAS's deterministic signal engine."""

    def __init__(self, config=None):

        super().__init__("Technical Analyst", config=config)

        self.market = MarketDataAdapter()

        # Latest volume confirmation is exposed separately
        # from AnalysisResult so the existing contract remains
        # unchanged.
        self.volume_confirmation = None

    def analyze(self, symbol: str) -> AnalysisResult:

        data = self.market.get(symbol)

        # The signal engine owns technical direction. The analyst remains
        # responsible for translating that signal into the existing
        # AnalysisResult contract used by ATLAS's decision layer.
        signal = generate_technical_signal(data)
        action = signal.action

        if action.value == "BUY":
            confidence = 88
            evidence = 85
            reasoning = [
                self.t("price_above_ma20"),
                self.t("ma20_above_ma50"),
                self.t("overall_trend_bullish"),
            ]
        elif action.value == "SELL":
            confidence = 88
            evidence = 85
            reasoning = [
                self.t("price_below_ma20"),
                self.t("ma20_below_ma50"),
                self.t("overall_trend_bearish"),
            ]
        else:
            confidence = 65
            evidence = 65
            reasoning = [
                self.t("mixed_market_trend"),
                self.t("waiting_confirmation"),
            ]

        reasoning.append(
            f"Technical signal engine confidence: {signal.confidence}/100."
        )

        reasoning.extend(signal.reasons)

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

        # -------------------------------------------------
        # Volume Confirmation
        #
        # Volume confirms or weakens the existing technical
        # direction. It never creates the direction.
        # -------------------------------------------------

        self.volume_confirmation = confirm_volume(
            action=action.value,
            volume_level=volume.level,
            volume_ratio=volume.volume_ratio,
        )

        reasoning.append(
            self.volume_confirmation.interpretation
        )

        return AnalysisResult(

            analyst=self.name,

            symbol=data.symbol,

            action=action,

            confidence=confidence,

            evidence=evidence,

            reasoning=reasoning,

        )
