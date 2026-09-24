"""
ATLAS Signal Evidence Layer.

Describes technical and market evidence without making
BUY / SELL / WAIT decisions.

The purpose is to provide structured evidence that can
later be evaluated by the prediction-learning system.
"""

from dataclasses import dataclass

from atlas.trading.indicator_engine import IndicatorSnapshot
from atlas.trading.multi_timeframe_analysis import (
    MultiTimeframeAnalysis,
)


@dataclass(slots=True)
class SignalEvidence:
    trend: str
    momentum: str
    volatility: str
    volume: str
    breakout: str

    rsi_signal: str
    macd_signal: str
    bollinger_signal: str
    adx_signal: str

    technical_quality: str

    multi_timeframe_signal: str
    multi_timeframe_alignment: float

    evidence_quality: str


class SignalEvidenceAnalyzer:
    """Extract structured evidence from existing analysis."""

    def analyze(
        self,
        indicators: IndicatorSnapshot,
        multi_timeframe: MultiTimeframeAnalysis,
        data_freshness: str | None = None,
    ) -> SignalEvidence:

        trend = self._trend(indicators)

        momentum = self._momentum(indicators)

        volatility = self._volatility(
            indicators
        )

        volume = self._volume(indicators)

        breakout = self._breakout(
            indicators
        )

        rsi_signal = self._rsi(
            indicators
        )

        macd_signal = self._macd(
            indicators
        )

        bollinger_signal = self._bollinger(
            indicators
        )

        adx_signal = self._adx(
            indicators
        )

        technical_quality = (
            indicators.data_quality
        )

        evidence_quality = self._quality(
            indicators,
            multi_timeframe,
            data_freshness=data_freshness,
        )

        return SignalEvidence(
            trend=trend,
            momentum=momentum,
            volatility=volatility,
            volume=volume,
            breakout=breakout,
            rsi_signal=rsi_signal,
            macd_signal=macd_signal,
            bollinger_signal=bollinger_signal,
            adx_signal=adx_signal,
            technical_quality=technical_quality,
            multi_timeframe_signal=(
                multi_timeframe.overall_signal
            ),
            multi_timeframe_alignment=(
                multi_timeframe.alignment
            ),
            evidence_quality=evidence_quality,
        )

    @staticmethod
    def _trend(
        indicators: IndicatorSnapshot,
    ) -> str:

        if (
            indicators.ema20 is not None
            and indicators.ema50 is not None
        ):
            if (
                indicators.ema20
                > indicators.ema50
            ):
                return "BULLISH"

            if (
                indicators.ema20
                < indicators.ema50
            ):
                return "BEARISH"

        return "NEUTRAL"

    @staticmethod
    def _momentum(
        indicators: IndicatorSnapshot,
    ) -> str:

        if indicators.rsi14 is None:
            return "UNKNOWN"

        if indicators.rsi14 >= 60:
            return "POSITIVE"

        if indicators.rsi14 <= 40:
            return "NEGATIVE"

        return "NEUTRAL"

    @staticmethod
    def _volatility(
        indicators: IndicatorSnapshot,
    ) -> str:

        if indicators.atr_percent is None:
            return "UNKNOWN"

        if indicators.atr_percent >= 5.0:
            return "HIGH"

        if indicators.atr_percent <= 1.0:
            return "LOW"

        return "NORMAL"

    @staticmethod
    def _volume(
        indicators: IndicatorSnapshot,
    ) -> str:

        if indicators.relative_volume is None:
            return "UNKNOWN"

        if indicators.relative_volume >= 1.5:
            return "ABOVE_AVERAGE"

        if indicators.relative_volume <= 0.7:
            return "BELOW_AVERAGE"

        return "NORMAL"

    @staticmethod
    def _breakout(
        indicators: IndicatorSnapshot,
    ) -> str:

        if indicators.breakout50:
            return "BREAKOUT_50"

        if indicators.breakout20:
            return "BREAKOUT_20"

        return "NONE"

    @staticmethod
    def _rsi(
        indicators: IndicatorSnapshot,
    ) -> str:

        if indicators.rsi14 is None:
            return "UNKNOWN"

        if indicators.rsi14 >= 70:
            return "OVERBOUGHT"

        if indicators.rsi14 <= 30:
            return "OVERSOLD"

        if indicators.rsi14 >= 55:
            return "BULLISH"

        if indicators.rsi14 <= 45:
            return "BEARISH"

        return "NEUTRAL"

    @staticmethod
    def _macd(
        indicators: IndicatorSnapshot,
    ) -> str:

        if (
            indicators.macd is None
            or indicators.macd_signal is None
        ):
            return "UNKNOWN"

        if (
            indicators.macd
            > indicators.macd_signal
        ):
            return "BULLISH"

        if (
            indicators.macd
            < indicators.macd_signal
        ):
            return "BEARISH"

        return "NEUTRAL"

    @staticmethod
    def _bollinger(
        indicators: IndicatorSnapshot,
    ) -> str:

        if indicators.bollinger_position is None:
            return "UNKNOWN"

        if indicators.bollinger_position >= 0.8:
            return "UPPER_ZONE"

        if indicators.bollinger_position <= 0.2:
            return "LOWER_ZONE"

        return "MID_ZONE"

    @staticmethod
    def _adx(
        indicators: IndicatorSnapshot,
    ) -> str:

        if indicators.adx14 is None:
            return "UNKNOWN"

        if indicators.adx14 >= 25:
            return "STRONG_TREND"

        if indicators.adx14 <= 15:
            return "WEAK_TREND"

        return "MODERATE_TREND"

    @staticmethod
    def _quality(
        indicators: IndicatorSnapshot,
        multi_timeframe: MultiTimeframeAnalysis,
        data_freshness: str | None = None,
    ) -> str:

        if data_freshness == "STALE":
            return "POOR"

        if (
            indicators.data_quality == "MISSING"
            or multi_timeframe.data_quality
            == "MISSING"
        ):
            return "MISSING"

        if (
            indicators.data_quality == "POOR"
            or multi_timeframe.data_quality
            == "POOR"
        ):
            return "POOR"

        if (
            indicators.data_quality == "PARTIAL"
            or multi_timeframe.data_quality
            == "PARTIAL"
        ):
            return "PARTIAL"

        return "GOOD"
