"""Intraday breakout trading algorithm."""

from math import isfinite

from atlas.algorithms.base import AlgorithmSignal
from atlas.models.action import Action


class IntradayBreakoutAlgorithm:
    """Conservative range-breakout signal for intraday trading.

    The algorithm deliberately reports a signal only. It does not place
    orders, estimate a profitable edge, or bypass ATLAS risk controls.
    """

    name = "intraday_breakout"

    def __init__(
        self,
        timeframe: str = "5m",
        lookback: int = 12,
        breakout_threshold_percent: float = 0.20,
    ):
        if lookback < 2:
            raise ValueError("lookback must be at least 2")

        if breakout_threshold_percent < 0:
            raise ValueError(
                "breakout_threshold_percent must be non-negative"
            )

        self.timeframe = timeframe
        self.lookback = lookback
        self.breakout_threshold_percent = (
            breakout_threshold_percent
        )

    def generate_signal(
        self,
        symbol: str,
        candles: list[dict],
    ) -> AlgorithmSignal:
        required = self.lookback + 1

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

        latest = closes[-1]
        previous = closes[-self.lookback - 1:-1]

        range_high = max(previous)
        range_low = min(previous)

        upside_breakout = (
            (latest / range_high) - 1.0
        ) * 100.0

        downside_breakout = (
            (latest / range_low) - 1.0
        ) * 100.0

        threshold = self.breakout_threshold_percent

        if upside_breakout > threshold:
            action = Action.BUY
            breakout_percent = upside_breakout
            direction = "upside"
        elif downside_breakout < -threshold:
            action = Action.SELL
            breakout_percent = downside_breakout
            direction = "downside"
        else:
            action = Action.HOLD
            breakout_percent = 0.0
            direction = "none"

        strength = min(
            1.0,
            abs(breakout_percent) / (
                threshold * 4.0
            )
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

        confidence = round(
            50.0 + 40.0 * strength,
            4,
        )

        reasoning = [
            f"{self.name} timeframe: {self.timeframe}.",
            f"Range high: {range_high:.4f}.",
            f"Range low: {range_low:.4f}.",
            f"Latest close: {latest:.4f}.",
            f"Breakout direction: {direction}.",
        ]

        if action is Action.BUY:
            reasoning.append(
                f"Upside breakout exceeds threshold "
                f"by {breakout_percent:.4f}%."
            )
        elif action is Action.SELL:
            reasoning.append(
                f"Downside breakout exceeds threshold "
                f"by {abs(breakout_percent):.4f}%."
            )
        else:
            reasoning.append(
                "Price remains inside the configured breakout range."
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
