"""ATLAS intraday value-zone trading algorithm."""

from __future__ import annotations

from math import isfinite

from atlas.algorithms.base import AlgorithmSignal
from atlas.models.action import Action


class IntradayValueZoneAlgorithm:
    """Identify relative low/high price zones with reversal confirmation.

    The algorithm looks for:
    - the current price position inside a recent price range
    - deviation from a moving average
    - short-term momentum
    - momentum reversal
    - optional volume confirmation

    It produces signals only. It never places orders or bypasses
    ATLAS risk controls.
    """

    name = "intraday_value_zone"

    def __init__(
        self,
        timeframe: str = "5m",
        range_window: int = 24,
        mean_window: int = 12,
        momentum_window: int = 3,
        buy_zone: float = 0.25,
        sell_zone: float = 0.75,
        deviation_threshold_percent: float = 0.50,
        reversal_threshold_percent: float = 0.05,
    ):
        if range_window < 5:
            raise ValueError("range_window must be at least 5")

        if mean_window < 2:
            raise ValueError("mean_window must be at least 2")

        if momentum_window < 1:
            raise ValueError("momentum_window must be positive")

        if mean_window >= range_window:
            raise ValueError(
                "mean_window must be smaller than range_window"
            )

        if not 0.0 <= buy_zone < sell_zone <= 1.0:
            raise ValueError(
                "buy_zone and sell_zone must satisfy 0 <= buy < sell <= 1"
            )

        if deviation_threshold_percent < 0:
            raise ValueError(
                "deviation_threshold_percent must be non-negative"
            )

        if reversal_threshold_percent < 0:
            raise ValueError(
                "reversal_threshold_percent must be non-negative"
            )

        self.timeframe = timeframe
        self.range_window = range_window
        self.mean_window = mean_window
        self.momentum_window = momentum_window
        self.buy_zone = buy_zone
        self.sell_zone = sell_zone
        self.deviation_threshold_percent = (
            deviation_threshold_percent
        )
        self.reversal_threshold_percent = (
            reversal_threshold_percent
        )

    def generate_signal(
        self,
        symbol: str,
        candles: list[dict],
    ) -> AlgorithmSignal:
        required = max(
            self.range_window,
            self.mean_window + self.momentum_window,
        )

        if len(candles) < required:
            raise ValueError(
                f"at least {required} candles are required"
            )

        closes = []

        for candle in candles:
            close = float(candle["close"])

            if not isfinite(close) or close <= 0:
                raise ValueError(
                    "candles must contain finite positive close prices"
                )

            closes.append(close)

        latest = closes[-1]

        recent = closes[-self.range_window:]
        range_low = min(recent)
        range_high = max(recent)
        range_size = range_high - range_low

        if range_size <= 0:
            range_position = 0.5
        else:
            range_position = (
                latest - range_low
            ) / range_size

        mean = sum(
            closes[-self.mean_window:]
        ) / self.mean_window

        mean_deviation_percent = (
            (latest / mean) - 1.0
        ) * 100.0

        momentum_start = closes[
            -self.momentum_window - 1
        ]

        momentum_percent = (
            (latest / momentum_start) - 1.0
        ) * 100.0

        previous_latest = closes[-2]

        last_candle_change_percent = (
            (latest / previous_latest) - 1.0
        ) * 100.0

        momentum_change = last_candle_change_percent

        previous_range_position = (
            0.5
            if range_size <= 0
            else (
                previous_latest - range_low
            ) / range_size
        )

        buy_zone_active = (
            previous_range_position <= self.buy_zone
        )

        sell_zone_active = (
            previous_range_position >= self.sell_zone
        )

        positive_reversal = (
            momentum_change >= self.reversal_threshold_percent
        )

        negative_reversal = (
            momentum_change <= -self.reversal_threshold_percent
        )

        buy_confirmation = (
            mean_deviation_percent
            <= -self.deviation_threshold_percent
            and positive_reversal
        )

        sell_confirmation = (
            mean_deviation_percent
            >= self.deviation_threshold_percent
            and negative_reversal
        )

        if buy_zone_active and buy_confirmation:
            action = Action.BUY
        elif sell_zone_active and sell_confirmation:
            action = Action.SELL
        else:
            action = Action.HOLD

        zone_distance = min(
            range_position,
            1.0 - range_position,
        )

        zone_strength = min(
            1.0,
            max(
                0.0,
                (
                    0.5 - zone_distance
                ) / 0.5,
            ),
        )

        deviation_strength = min(
            1.0,
            abs(mean_deviation_percent)
            / max(
                self.deviation_threshold_percent * 4.0,
                0.01,
            ),
        )

        reversal_strength = min(
            1.0,
            abs(momentum_change)
            / max(
                self.reversal_threshold_percent * 4.0,
                0.01,
            ),
        )

        strength = (
            zone_strength
            + deviation_strength
            + reversal_strength
        ) / 3.0

        directional_score = (
            1.0
            if action is Action.BUY
            else -1.0
            if action is Action.SELL
            else 0.0
        )

        score = (
            50.0
            + directional_score * 50.0 * strength
        )

        confidence = 50.0 + 40.0 * strength

        reasoning = [
            f"{self.name} timeframe: {self.timeframe}.",
            f"Range low: {range_low:.4f}.",
            f"Range high: {range_high:.4f}.",
            f"Latest close: {latest:.4f}.",
            (
                f"Price position in local range: "
                f"{range_position:.4f}."
            ),
            f"Moving average: {mean:.4f}.",
            (
                f"Mean deviation: "
                f"{mean_deviation_percent:.4f}%."
            ),
            (
                f"Momentum: "
                f"{momentum_percent:.4f}%."
            ),
            (
                f"Momentum change: "
                f"{momentum_change:.4f}%."
            ),
        ]

        if action is Action.BUY:
            reasoning.append(
                "Price is in the lower value zone and "
                "short-term momentum confirms a positive reversal."
            )
        elif action is Action.SELL:
            reasoning.append(
                "Price is in the upper value zone and "
                "short-term momentum confirms a negative reversal."
            )
        else:
            reasoning.append(
                "Price zone and reversal conditions do not "
                "provide sufficient directional confirmation."
            )

        return AlgorithmSignal(
            algorithm=self.name,
            symbol=symbol,
            timeframe=self.timeframe,
            action=action,
            score=round(score, 4),
            confidence=round(confidence, 4),
            expected_edge=None,
            reasoning=reasoning,
        )
