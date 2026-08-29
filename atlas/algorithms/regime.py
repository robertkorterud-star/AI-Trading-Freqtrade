"""ATLAS market regime detection."""

from dataclasses import dataclass
from enum import Enum
from math import isfinite


class MarketRegime(str, Enum):
    """High-level market regimes used by ATLAS."""

    BULL_TREND = "bull_trend"
    BEAR_TREND = "bear_trend"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"


@dataclass(frozen=True, slots=True)
class MarketRegimeResult:
    """Structured market regime classification."""

    symbol: str
    timeframe: str
    regime: MarketRegime
    trend_score: float
    volatility_percent: float
    confidence: float
    reasoning: list[str]


class MarketRegimeEngine:
    """Deterministically classify the current market regime.

    The engine is deliberately descriptive only. It does not place
    orders and does not make an independent BUY or SELL decision.
    """

    name = "market_regime"

    def __init__(
        self,
        timeframe: str = "1h",
        trend_window: int = 20,
        volatility_window: int = 20,
        bull_threshold: float = 1.0,
        bear_threshold: float = -1.0,
        high_volatility_threshold: float = 4.0,
    ):
        if trend_window < 2:
            raise ValueError("trend_window must be at least 2")

        if volatility_window < 2:
            raise ValueError("volatility_window must be at least 2")

        if bull_threshold <= 0:
            raise ValueError("bull_threshold must be positive")

        if bear_threshold >= 0:
            raise ValueError("bear_threshold must be negative")

        if high_volatility_threshold <= 0:
            raise ValueError(
                "high_volatility_threshold must be positive"
            )

        self.timeframe = timeframe
        self.trend_window = trend_window
        self.volatility_window = volatility_window
        self.bull_threshold = bull_threshold
        self.bear_threshold = bear_threshold
        self.high_volatility_threshold = high_volatility_threshold

    def analyze(
        self,
        symbol: str,
        candles: list[dict],
    ) -> MarketRegimeResult:
        required = max(
            self.trend_window + 1,
            self.volatility_window + 1,
        )

        if len(candles) < required:
            raise ValueError(
                f"at least {required} candles are required"
            )

        closes = [
            float(candle["close"])
            for candle in candles
        ]

        if any(
            not isfinite(price) or price <= 0
            for price in closes
        ):
            raise ValueError(
                "candles must contain finite positive close prices"
            )

        trend_start = closes[-self.trend_window - 1]
        latest = closes[-1]

        trend_score = self._return_percent(
            trend_start,
            latest,
        )

        volatility_percent = self._average_absolute_return(
            closes[-self.volatility_window - 1:],
        )

        if volatility_percent >= self.high_volatility_threshold:
            regime = MarketRegime.HIGH_VOLATILITY
        elif trend_score >= self.bull_threshold:
            regime = MarketRegime.BULL_TREND
        elif trend_score <= self.bear_threshold:
            regime = MarketRegime.BEAR_TREND
        else:
            regime = MarketRegime.SIDEWAYS

        trend_strength = min(
            1.0,
            abs(trend_score)
            / max(
                self.bull_threshold,
                abs(self.bear_threshold),
            ),
        )

        volatility_strength = min(
            1.0,
            volatility_percent
            / self.high_volatility_threshold,
        )

        if regime is MarketRegime.HIGH_VOLATILITY:
            confidence = 50.0 + volatility_strength * 40.0
        else:
            confidence = 50.0 + trend_strength * 40.0

        confidence = round(
            min(90.0, confidence),
            4,
        )

        reasoning = [
            f"{self.name}: classified market regime.",
            f"Timeframe: {self.timeframe}.",
            f"Trend return: {trend_score:.4f}%.",
            f"Average absolute return: "
            f"{volatility_percent:.4f}%.",
            f"Regime: {regime.value}.",
        ]

        if regime is MarketRegime.BULL_TREND:
            reasoning.append(
                "Price trend is sufficiently positive."
            )
        elif regime is MarketRegime.BEAR_TREND:
            reasoning.append(
                "Price trend is sufficiently negative."
            )
        elif regime is MarketRegime.HIGH_VOLATILITY:
            reasoning.append(
                "Recent price movement exceeds the "
                "high-volatility threshold."
            )
        else:
            reasoning.append(
                "No sufficiently strong directional trend "
                "was detected."
            )

        return MarketRegimeResult(
            symbol=symbol,
            timeframe=self.timeframe,
            regime=regime,
            trend_score=round(trend_score, 4),
            volatility_percent=round(
                volatility_percent,
                4,
            ),
            confidence=confidence,
            reasoning=reasoning,
        )

    @staticmethod
    def _return_percent(
        start: float,
        end: float,
    ) -> float:
        return ((end / start) - 1.0) * 100.0

    @staticmethod
    def _average_absolute_return(
        closes: list[float],
    ) -> float:
        returns = [
            abs(
                ((current / previous) - 1.0) * 100.0
            )
            for previous, current in zip(
                closes,
                closes[1:],
            )
        ]

        if not returns:
            return 0.0

        return sum(returns) / len(returns)
