"""
ATLAS Prediction Feature Vector.

Converts structured SignalEvidence into numerical features
suitable for historical analysis and future machine learning.

This module MUST NOT make BUY / SELL / WAIT decisions.
"""

from dataclasses import dataclass

from atlas.trading.signal_evidence import SignalEvidence


@dataclass(slots=True)
class PredictionFeatureVector:
    trend: float
    momentum: float
    volatility: float
    volume: float
    breakout: float

    rsi_signal: float
    macd_signal: float
    bollinger_signal: float
    adx_signal: float

    multi_timeframe_signal: float
    multi_timeframe_alignment: float

    technical_quality: float
    evidence_quality: float


class PredictionFeatureBuilder:
    """Convert SignalEvidence into ML-friendly numerical features."""

    def build(
        self,
        evidence: SignalEvidence,
    ) -> PredictionFeatureVector:

        return PredictionFeatureVector(
            trend=self._trend(
                evidence.trend
            ),
            momentum=self._momentum(
                evidence.momentum
            ),
            volatility=self._volatility(
                evidence.volatility
            ),
            volume=self._volume(
                evidence.volume
            ),
            breakout=self._breakout(
                evidence.breakout
            ),
            rsi_signal=self._direction(
                evidence.rsi_signal
            ),
            macd_signal=self._direction(
                evidence.macd_signal
            ),
            bollinger_signal=self._bollinger(
                evidence.bollinger_signal
            ),
            adx_signal=self._adx(
                evidence.adx_signal
            ),
            multi_timeframe_signal=(
                self._direction(
                    evidence.multi_timeframe_signal
                )
            ),
            multi_timeframe_alignment=(
                self._alignment(
                    evidence.multi_timeframe_alignment
                )
            ),
            technical_quality=self._quality(
                evidence.technical_quality
            ),
            evidence_quality=self._quality(
                evidence.evidence_quality
            ),
        )

    @staticmethod
    def _trend(value: str) -> float:

        return {
            "BULLISH": 1.0,
            "NEUTRAL": 0.0,
            "BEARISH": -1.0,
        }.get(value, 0.0)

    @staticmethod
    def _momentum(value: str) -> float:

        return {
            "POSITIVE": 1.0,
            "NEUTRAL": 0.0,
            "NEGATIVE": -1.0,
        }.get(value, 0.0)

    @staticmethod
    def _volatility(value: str) -> float:

        return {
            "HIGH": 1.0,
            "NORMAL": 0.0,
            "LOW": -1.0,
        }.get(value, 0.0)

    @staticmethod
    def _volume(value: str) -> float:

        return {
            "ABOVE_AVERAGE": 1.0,
            "NORMAL": 0.0,
            "BELOW_AVERAGE": -1.0,
        }.get(value, 0.0)

    @staticmethod
    def _breakout(value: str) -> float:

        return {
            "BREAKOUT_50": 1.0,
            "BREAKOUT_20": 0.75,
            "NONE": 0.0,
        }.get(value, 0.0)

    @staticmethod
    def _direction(value: str) -> float:

        return {
            "BULLISH": 1.0,
            "BUY": 1.0,
            "POSITIVE": 1.0,
            "BEARISH": -1.0,
            "SELL": -1.0,
            "NEGATIVE": -1.0,
            "NEUTRAL": 0.0,
            "WAIT": 0.0,
            "UNKNOWN": 0.0,
            "OVERSOLD": 0.0,
            "OVERBOUGHT": 0.0,
        }.get(value, 0.0)

    @staticmethod
    def _bollinger(value: str) -> float:

        return {
            "UPPER_ZONE": 1.0,
            "MID_ZONE": 0.0,
            "LOWER_ZONE": -1.0,
        }.get(value, 0.0)

    @staticmethod
    def _adx(value: str) -> float:

        return {
            "STRONG_TREND": 1.0,
            "MODERATE_TREND": 0.5,
            "WEAK_TREND": 0.0,
        }.get(value, 0.0)

    @staticmethod
    def _alignment(value: float) -> float:

        if value < 0:
            return 0.0

        if value > 1:
            return min(
                value / 100.0,
                1.0,
            )

        return value

    @staticmethod
    def _quality(value: str) -> float:

        return {
            "GOOD": 1.0,
            "PARTIAL": 0.5,
            "POOR": 0.25,
            "MISSING": 0.0,
        }.get(value, 0.0)
