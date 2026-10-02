"""Intraday VWAP trading algorithm."""

from math import isfinite, tanh

from atlas.algorithms.base import AlgorithmSignal
from atlas.models.action import Action


class IntradayVWAPAlgorithm:
    """Intraday volume-weighted price reference algorithm.

    VWAP provides an intraday estimate of the average traded price
    weighted by volume. The algorithm combines price position relative
    to VWAP with short-term directional momentum.

    The algorithm reports a signal only. It does not place orders or
    bypass ATLAS risk controls.
    """

    name = "intraday_vwap"

    def __init__(
        self,
        timeframe: str = "5m",
        window: int = 20,
        deviation_threshold_percent: float = 0.15,
        momentum_window: int = 3,
        momentum_threshold_percent: float = 0.05,
    ):
        if window < 2:
            raise ValueError("window must be at least 2")

        if momentum_window < 1:
            raise ValueError("momentum_window must be positive")

        if momentum_window >= window:
            raise ValueError(
                "momentum_window must be smaller than window"
            )

        if deviation_threshold_percent < 0:
            raise ValueError(
                "deviation_threshold_percent must be non-negative"
            )

        if momentum_threshold_percent < 0:
            raise ValueError(
                "momentum_threshold_percent must be non-negative"
            )

        self.timeframe = timeframe
        self.window = window
        self.deviation_threshold_percent = (
            deviation_threshold_percent
        )
        self.momentum_window = momentum_window
        self.momentum_threshold_percent = momentum_threshold_percent

    def generate_signal(
        self,
        symbol: str,
        candles: list[dict],
    ) -> AlgorithmSignal:
        required = self.window + self.momentum_window

        if len(candles) < required:
            raise ValueError(
                f"at least {required} candles are required"
            )

        recent = candles[-self.window:]

        typical_prices = []

        for candle in recent:
            high = float(candle["high"])
            low = float(candle["low"])
            close = float(candle["close"])
            volume = float(candle["volume"])

            if any(
                not isfinite(value)
                for value in (high, low, close, volume)
            ):
                raise ValueError(
                    "candles must contain finite OHLCV values"
                )

            if high <= 0 or low <= 0 or close <= 0:
                raise ValueError(
                    "candles must contain positive OHLC prices"
                )

            if volume < 0:
                raise ValueError(
                    "candles must contain non-negative volume"
                )

            if high < low:
                raise ValueError(
                    "candle high must be greater than or equal to low"
                )

            typical_prices.append(
                (high + low + close) / 3.0
            )

        total_volume = sum(
            float(candle["volume"])
            for candle in recent
        )

        latest_close = float(candles[-1]["close"])

        if total_volume <= 0:
            raise ValueError(
                "VWAP requires positive total volume"
            )

        vwap = sum(
            typical_price * float(candle["volume"])
            for typical_price, candle in zip(
                typical_prices,
                recent,
            )
        ) / total_volume

        deviation_percent = (
            (latest_close / vwap) - 1.0
        ) * 100.0

        momentum_start = candles[
            -self.momentum_window - 1
        ]["close"]

        momentum_percent = (
            (latest_close / float(momentum_start)) - 1.0
        ) * 100.0

        deviation_threshold = (
            self.deviation_threshold_percent
        )
        momentum_threshold = (
            self.momentum_threshold_percent
        )

        if (
            deviation_percent > deviation_threshold
            and momentum_percent > momentum_threshold
        ):
            action = Action.BUY
        elif (
            deviation_percent < -deviation_threshold
            and momentum_percent < -momentum_threshold
        ):
            action = Action.SELL
        else:
            action = Action.HOLD

        normalized_deviation = min(
            1.0,
            abs(deviation_percent) / max(
                deviation_threshold * 4.0,
                0.01,
            ),
        )

        normalized_momentum = min(
            1.0,
            abs(momentum_percent) / max(
                momentum_threshold * 4.0,
                0.01,
            ),
        )

        strength = (
            normalized_deviation
            + normalized_momentum
        ) / 2.0

        score = 50.0 + 50.0 * tanh(strength * 2.0)

        if action is Action.HOLD:
            score = 50.0
        elif action is Action.SELL:
            score = 100.0 - score

        confidence = 50.0 + 40.0 * strength

        reasoning = [
            f"{self.name} timeframe: {self.timeframe}.",
            f"VWAP: {vwap:.4f}.",
            f"Latest close: {latest_close:.4f}.",
            f"VWAP deviation: {deviation_percent:.4f}%.",
            f"Short momentum: {momentum_percent:.4f}%.",
        ]

        if action is Action.HOLD:
            reasoning.append(
                "Price position and momentum do not confirm "
                "a directional VWAP signal."
            )
        else:
            reasoning.append(
                f"Price position and momentum align for "
                f"{action.value}."
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
