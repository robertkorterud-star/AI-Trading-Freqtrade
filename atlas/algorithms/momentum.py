"""Intraday momentum trading algorithm."""

from math import isfinite, tanh

from atlas.algorithms.base import AlgorithmSignal
from atlas.models.action import Action
from atlas.trading.indicators import calculate_adx, calculate_ema, calculate_macd, calculate_rsi


class IntradayMomentumAlgorithm:
    """Conservative momentum signal using price and momentum indicators.

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
        rsi_period: int = 14,
        fast_ema_period: int = 12,
        slow_ema_period: int = 26,
        macd_signal_period: int = 9,
        adx_period: int = 14,
        adx_threshold: float = 20.0,
    ):
        if short_window < 1:
            raise ValueError("short_window must be positive")
        if long_window <= short_window:
            raise ValueError("long_window must exceed short_window")
        if signal_threshold_percent < 0:
            raise ValueError("signal_threshold_percent must be non-negative")
        if min(
            rsi_period,
            fast_ema_period,
            slow_ema_period,
            macd_signal_period,
            adx_period,
        ) <= 0:
            raise ValueError("indicator periods must be positive")
        if fast_ema_period >= slow_ema_period:
            raise ValueError("fast_ema_period must be smaller than slow_ema_period")
        if adx_threshold < 0:
            raise ValueError("adx_threshold must be non-negative")

        self.timeframe = timeframe
        self.short_window = short_window
        self.long_window = long_window
        self.signal_threshold_percent = signal_threshold_percent
        self.rsi_period = rsi_period
        self.fast_ema_period = fast_ema_period
        self.slow_ema_period = slow_ema_period
        self.macd_signal_period = macd_signal_period
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold

    def generate_signal(
        self,
        symbol: str,
        candles: list[dict],
    ) -> AlgorithmSignal:
        required = self.long_window + 1
        if len(candles) < required:
            raise ValueError(f"at least {required} candles are required")

        closes = [float(candle["close"]) for candle in candles]
        highs = [float(candle.get("high", candle["close"])) for candle in candles]
        lows = [float(candle.get("low", candle["close"])) for candle in candles]
        if any(not isfinite(price) or price <= 0 for price in closes):
            raise ValueError("candles must contain finite positive close prices")
        if any(
            not isfinite(value) or value <= 0
            for series in (highs, lows)
            for value in series
        ):
            raise ValueError("candles must contain finite positive OHLC prices")

        latest = closes[-1]
        short_return = self._return_percent(closes[-self.short_window - 1], latest)
        long_return = self._return_percent(closes[-self.long_window - 1], latest)

        rsi = calculate_rsi(closes, self.rsi_period)[-1]
        fast_ema = calculate_ema(closes, self.fast_ema_period)[-1]
        slow_ema = calculate_ema(closes, self.slow_ema_period)[-1]
        _, _, macd_histogram = calculate_macd(
            closes,
            self.fast_ema_period,
            self.slow_ema_period,
            self.macd_signal_period,
        )
        macd_hist = macd_histogram[-1]
        adx_values, plus_di_values, minus_di_values = calculate_adx(
            highs,
            lows,
            closes,
            self.adx_period,
        )
        adx = adx_values[-1]
        plus_di = plus_di_values[-1]
        minus_di = minus_di_values[-1]

        evidence: list[float] = []
        reasoning = [
            f"{self.name} timeframe: {self.timeframe}.",
            f"Short momentum: {short_return:.4f}%.",
            f"Long momentum: {long_return:.4f}%.",
        ]

        price_up = short_return > self.signal_threshold_percent and long_return > self.signal_threshold_percent
        price_down = short_return < -self.signal_threshold_percent and long_return < -self.signal_threshold_percent
        if price_up or price_down:
            evidence.append(1.0 if price_up else -1.0)

        if rsi > 55:
            evidence.append(1.0)
            reasoning.append(f"RSI supports bullish momentum: {rsi:.2f}.")
        elif rsi < 45:
            evidence.append(-1.0)
            reasoning.append(f"RSI supports bearish momentum: {rsi:.2f}.")
        else:
            reasoning.append(f"RSI is neutral: {rsi:.2f}.")

        if macd_hist is not None:
            if macd_hist > 0:
                evidence.append(1.0)
                reasoning.append(f"MACD histogram is positive: {macd_hist:.6f}.")
            elif macd_hist < 0:
                evidence.append(-1.0)
                reasoning.append(f"MACD histogram is negative: {macd_hist:.6f}.")
            else:
                reasoning.append("MACD histogram is neutral.")

        if fast_ema is not None and slow_ema is not None:
            if fast_ema > slow_ema:
                evidence.append(1.0)
                reasoning.append("EMA alignment is bullish (fast EMA above slow EMA).")
            elif fast_ema < slow_ema:
                evidence.append(-1.0)
                reasoning.append("EMA alignment is bearish (fast EMA below slow EMA).")
            else:
                reasoning.append("EMA alignment is neutral.")

        if adx is not None and plus_di is not None and minus_di is not None:
            if adx >= self.adx_threshold and plus_di > minus_di:
                evidence.append(1.0)
                reasoning.append(f"ADX confirms bullish trend strength: {adx:.2f}.")
            elif adx >= self.adx_threshold and minus_di > plus_di:
                evidence.append(-1.0)
                reasoning.append(f"ADX confirms bearish trend strength: {adx:.2f}.")
            else:
                reasoning.append(f"ADX does not confirm a strong directional trend: {adx:.2f}.")

        average_evidence = sum(evidence) / len(evidence) if evidence else 0.0
        if average_evidence >= 0.60:
            action = Action.BUY
        elif average_evidence <= -0.60:
            action = Action.SELL
        else:
            action = Action.HOLD

        strength = min(1.0, abs(average_evidence))
        score = 50.0 + 50.0 * tanh(strength * 2.0)
        if action is Action.HOLD:
            score = 50.0
        elif action is Action.SELL:
            score = 100.0 - score

        score = round(score, 4)
        confidence = round(50.0 + 40.0 * strength, 4)

        reasoning.append(f"Momentum indicator agreement: {average_evidence:.2f}.")
        reasoning.append(
            "Momentum evidence aligns for " + action.value + "."
            if action is not Action.HOLD
            else "Momentum evidence is mixed; holding."
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
