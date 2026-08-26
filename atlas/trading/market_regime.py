"""
ATLAS Market Regime Engine.

Classifies the current market environment from indicator features.

The regime is context only. It does not place trades and does not
produce BUY/SELL decisions.
"""

from dataclasses import dataclass

from atlas.trading.indicator_engine import IndicatorSnapshot


@dataclass(slots=True)
class MarketRegime:
    regime: str
    confidence: float
    trend_strength: float
    volatility_level: str
    breakout: bool
    reason: str


class MarketRegimeAnalyzer:
    """Classify market conditions from an IndicatorSnapshot."""

    def analyze(
        self,
        indicators: IndicatorSnapshot,
    ) -> MarketRegime:

        if indicators.data_quality == "MISSING":
            return MarketRegime(
                regime="UNKNOWN",
                confidence=0.0,
                trend_strength=0.0,
                volatility_level="UNKNOWN",
                breakout=False,
                reason="Market data is missing.",
            )

        volatility_level = self._volatility_level(
            indicators
        )

        breakout = bool(
            indicators.breakout20
            or indicators.breakout50
        )

        trend_strength = (
            indicators.adx14
            if indicators.adx14 is not None
            else 0.0
        )

        bullish_trend = self._bullish_trend(
            indicators
        )

        bearish_trend = self._bearish_trend(
            indicators
        )

        strong_trend = trend_strength >= 25.0

        if breakout and bullish_trend:
            return MarketRegime(
                regime="BREAKOUT_UP",
                confidence=self._confidence(
                    trend_strength,
                    85.0,
                ),
                trend_strength=round(
                    trend_strength,
                    2,
                ),
                volatility_level=volatility_level,
                breakout=True,
                reason=(
                    "Price is breaking above the recent "
                    "range with bullish trend structure."
                ),
            )

        if (
            breakout
            and bearish_trend
            and not bullish_trend
        ):
            return MarketRegime(
                regime="BREAKOUT_DOWN",
                confidence=self._confidence(
                    trend_strength,
                    85.0,
                ),
                trend_strength=round(
                    trend_strength,
                    2,
                ),
                volatility_level=volatility_level,
                breakout=True,
                reason=(
                    "Price is breaking below the recent "
                    "range with bearish trend structure."
                ),
            )

        if bullish_trend and strong_trend:
            return MarketRegime(
                regime="TRENDING_UP",
                confidence=self._confidence(
                    trend_strength,
                    80.0,
                ),
                trend_strength=round(
                    trend_strength,
                    2,
                ),
                volatility_level=volatility_level,
                breakout=False,
                reason=(
                    "Moving averages and momentum indicate "
                    "a strong bullish trend."
                ),
            )

        if bearish_trend and strong_trend:
            return MarketRegime(
                regime="TRENDING_DOWN",
                confidence=self._confidence(
                    trend_strength,
                    80.0,
                ),
                trend_strength=round(
                    trend_strength,
                    2,
                ),
                volatility_level=volatility_level,
                breakout=False,
                reason=(
                    "Moving averages and momentum indicate "
                    "a strong bearish trend."
                ),
            )

        if volatility_level == "HIGH":
            return MarketRegime(
                regime="HIGH_VOLATILITY",
                confidence=70.0,
                trend_strength=round(
                    trend_strength,
                    2,
                ),
                volatility_level=volatility_level,
                breakout=False,
                reason=(
                    "ATR and/or Bollinger width indicate "
                    "elevated volatility."
                ),
            )

        if volatility_level == "LOW":
            return MarketRegime(
                regime="LOW_VOLATILITY",
                confidence=70.0,
                trend_strength=round(
                    trend_strength,
                    2,
                ),
                volatility_level=volatility_level,
                breakout=False,
                reason=(
                    "ATR and Bollinger width indicate "
                    "compressed volatility."
                ),
            )

        return MarketRegime(
            regime="RANGING",
            confidence=60.0,
            trend_strength=round(
                trend_strength,
                2,
            ),
            volatility_level=volatility_level,
            breakout=False,
            reason=(
                "No strong directional trend or breakout "
                "was detected."
            ),
        )

    @staticmethod
    def _bullish_trend(
        indicators: IndicatorSnapshot,
    ) -> bool:

        moving_average_bullish = (
            indicators.ema20 is not None
            and indicators.ema50 is not None
            and indicators.ema20 > indicators.ema50
        )

        long_term_bullish = (
            indicators.sma200 is None
            or indicators.close > indicators.sma200
        )

        momentum_bullish = (
            indicators.rsi14 is None
            or indicators.rsi14 >= 50.0
        )

        return (
            moving_average_bullish
            and long_term_bullish
            and momentum_bullish
        )

    @staticmethod
    def _bearish_trend(
        indicators: IndicatorSnapshot,
    ) -> bool:

        moving_average_bearish = (
            indicators.ema20 is not None
            and indicators.ema50 is not None
            and indicators.ema20 < indicators.ema50
        )

        long_term_bearish = (
            indicators.sma200 is None
            or indicators.close < indicators.sma200
        )

        momentum_bearish = (
            indicators.rsi14 is None
            or indicators.rsi14 <= 50.0
        )

        return (
            moving_average_bearish
            and long_term_bearish
            and momentum_bearish
        )

    @staticmethod
    def _volatility_level(
        indicators: IndicatorSnapshot,
    ) -> str:

        atr_percent = indicators.atr_percent
        bollinger_width = indicators.bollinger_width

        if (
            atr_percent is None
            and bollinger_width is None
        ):
            return "UNKNOWN"

        high = (
            atr_percent is not None
            and atr_percent >= 3.0
        ) or (
            bollinger_width is not None
            and bollinger_width >= 8.0
        )

        low = (
            atr_percent is not None
            and atr_percent <= 1.0
        ) and (
            bollinger_width is None
            or bollinger_width <= 4.0
        )

        if high:
            return "HIGH"

        if low:
            return "LOW"

        return "NORMAL"

    @staticmethod
    def _confidence(
        trend_strength: float,
        base: float,
    ) -> float:

        if trend_strength >= 40.0:
            return min(
                95.0,
                base + 10.0,
            )

        if trend_strength >= 30.0:
            return min(
                92.0,
                base + 5.0,
            )

        return base
