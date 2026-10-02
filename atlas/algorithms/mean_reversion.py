"""Intraday mean-reversion trading algorithm."""

from math import isfinite

from atlas.algorithms.base import AlgorithmSignal
from atlas.models.action import Action


class IntradayMeanReversionAlgorithm:
    """Conservative price mean-reversion signal for intraday trading.

    The algorithm deliberately reports a signal only. It does not place
    orders, estimate a profitable edge, or bypass ATLAS risk controls.
    """

    name = "intraday_mean_reversion"

    def __init__(
        self,
        timeframe: str = "5m",
        window: int = 12,
        deviation_threshold_percent: float = 1.0,
    ):
        if window < 1:
            raise ValueError("window must be positive")

        if deviation_threshold_percent < 0:
            raise ValueError(
                "deviation_threshold_percent must be non-negative"
            )

        self.timeframe = timeframe
        self.window = window
        self.deviation_threshold_percent = (
            deviation_threshold_percent
        )

    def generate_signal(
        self,
        symbol: str,
        candles: list[dict],
    ) -> AlgorithmSignal:
        required = self.window + 1

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
        reference = sum(
            closes[-self.window - 1:-1]
        ) / self.window

        deviation_percent = (
            (latest / reference) - 1.0
        ) * 100.0

        threshold = self.deviation_threshold_percent

        if deviation_percent < -threshold:
            action = Action.BUY
        elif deviation_percent > threshold:
            action = Action.SELL
        else:
            action = Action.HOLD

        strength = min(
            1.0,
            abs(deviation_percent) / (
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
            f"Reference mean: {reference:.4f}.",
            f"Latest close: {latest:.4f}.",
            (
                f"Deviation from mean: "
                f"{deviation_percent:.4f}%."
            ),
        ]

        if action is Action.BUY:
            reasoning.append(
                "Price is below the mean by more than "
                "the configured threshold."
            )
        elif action is Action.SELL:
            reasoning.append(
                "Price is above the mean by more than "
                "the configured threshold."
            )
        else:
            reasoning.append(
                "Price deviation is within the configured "
                "mean-reversion threshold."
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
