"""Intraday momentum trading algorithm."""

from math import isfinite, tanh

from atlas.algorithms.base import AlgorithmSignal
from atlas.models.action import Action


class IntradayMomentumAlgorithm:
    """Conservative price-momentum signal for intraday trading.

    The algorithm deliberately reports a signal only. It does not place
    orders, estimate a profitable edge, or bypass ATLAS risk controls.
    """

    name = "intraday_momentum"

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
            raise ValueError("signal_threshold_percent must be non-negative")

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
        if any(not isfinite(price) or price <= 0 for price in closes):
            raise ValueError("candles must contain finite positive close prices")

        latest = closes[-1]
        short_return = self._return_percent(
            closes[-self.short_window - 1],
            latest,
        )
        long_return = self._return_percent(
            closes[-self.long_window - 1],
            latest,
        )

        threshold = self.signal_threshold_percent
        if short_return > threshold and long_return > threshold:
            action = Action.BUY
        elif short_return < -threshold and long_return < -threshold:
            action = Action.SELL
        else:
            action = Action.HOLD

        strength = min(
            1.0,
            (abs(short_return) + abs(long_return)) / 4.0,
        )
        score = round(50.0 + 50.0 * tanh(strength * 2.0), 4)
        confidence = round(50.0 + 40.0 * strength, 4)

        reasoning = [
            f"{self.name} timeframe: {self.timeframe}.",
            f"Short momentum: {short_return:.4f}%.",
            f"Long momentum: {long_return:.4f}%.",
        ]

        if action is Action.HOLD:
            reasoning.append("Momentum alignment is below the signal threshold.")
        else:
            reasoning.append(
                f"Short and long momentum align for {action.value}."
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

    @staticmethod
    def _return_percent(start: float, end: float) -> float:
        return ((end / start) - 1.0) * 100.0
