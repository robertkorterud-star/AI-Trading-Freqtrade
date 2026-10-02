"""Intraday trend-following trading algorithm."""

from math import isfinite

from atlas.algorithms.base import AlgorithmSignal
from atlas.models.action import Action


class IntradayTrendAlgorithm:
    """Conservative trend-following signal for intraday trading."""

    name = "intraday_trend"

    def __init__(
        self,
        timeframe: str = "5m",
        short_window: int = 3,
        long_window: int = 12,
        signal_threshold_percent: float = 0.20,
    ):
        if short_window < 1:
            raise ValueError("short_window must be positive")
        if long_window <= short_window:
            raise ValueError("long_window must exceed short_window")
        if signal_threshold_percent < 0:
            raise ValueError(
                "signal_threshold_percent must be non-negative"
            )

        self.timeframe = timeframe
        self.short_window = short_window
        self.long_window = long_window
        self.signal_threshold_percent = signal_threshold_percent

    def generate_signal(
        self,
        symbol: str,
        candles: list[dict],
    ) -> AlgorithmSignal:
        required = self.long_window + 1

        if len(candles) < required:
            raise ValueError(
                f"at least {required} candles are required"
            )

        closes = [float(candle["close"]) for candle in candles]

        if any(
            not isfinite(price) or price <= 0
            for price in closes
        ):
            raise ValueError(
                "candles must contain finite positive close prices"
            )

        short_average = (
            sum(closes[-self.short_window:])
            / self.short_window
        )
        long_average = (
            sum(closes[-self.long_window:])
            / self.long_window
        )

        spread_percent = (
            (short_average / long_average) - 1.0
        ) * 100.0

        threshold = self.signal_threshold_percent

        if spread_percent > threshold:
            action = Action.BUY
        elif spread_percent < -threshold:
            action = Action.SELL
        else:
            action = Action.HOLD

        strength = min(
            1.0,
            abs(spread_percent) / (threshold * 4.0)
            if threshold > 0
            else 0.0,
        )

        if action is Action.BUY:
            score = 50.0 + 50.0 * strength
        elif action is Action.SELL:
            score = 50.0 - 50.0 * strength
        else:
            score = 50.0

        score = round(score, 4)
        confidence = round(50.0 + 40.0 * strength, 4)

        reasoning = [
            f"{self.name} timeframe: {self.timeframe}.",
            f"Short average: {short_average:.4f}.",
            f"Long average: {long_average:.4f}.",
            f"Trend spread: {spread_percent:.4f}%.",
        ]

        if action is Action.BUY:
            reasoning.append(
                "Short average is above the long average."
            )
        elif action is Action.SELL:
            reasoning.append(
                "Short average is below the long average."
            )
        else:
            reasoning.append(
                "Trend spread is within the configured threshold."
            )

        return AlgorithmSignal(
            algorithm=self.name,
            symbol=symbol,
            timeframe=self.timeframe,
            action=action,
            score=score,
            confidence=confidence,
            expected_edge=None,
            reasoning=reasoning,
        )
