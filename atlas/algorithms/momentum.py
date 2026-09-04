"""Intraday momentum trading algorithm."""

from math import isfinite, tanh

from atlas.algorithms.base import AlgorithmSignal
from atlas.models.action import Action
from atlas.trading.indicators import calculate_adx, calculate_ema, calculate_macd, calculate_rsi


class IntradayMomentumAlgorithm:
    """Conservative momentum signal using price and momentum indicators."""

    name = "intraday_momentum"

    def __init__(self, timeframe="5m", short_window=3, long_window=12,
                 signal_threshold_percent=0.20, rsi_period=14,
                 fast_ema_period=12, slow_ema_period=26,
                 macd_signal_period=9, adx_period=14, adx_threshold=20.0):
        if short_window < 1 or long_window <= short_window:
            raise ValueError("invalid momentum windows")
        if signal_threshold_percent < 0:
            raise ValueError("signal_threshold_percent must be non-negative")
        if min(rsi_period, fast_ema_period, slow_ema_period, macd_signal_period, adx_period) <= 0:
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

    def generate_signal(self, symbol: str, candles: list[dict]) -> AlgorithmSignal:
        required = self.long_window + 1
        if len(candles) < required:
            raise ValueError(f"at least {required} candles are required")
        closes = [float(c["close"]) for c in candles]
        highs = [float(c.get("high", c["close"])) for c in candles]
        lows = [float(c.get("low", c["close"])) for c in candles]
        if any(not isfinite(v) or v <= 0 for s in (closes, highs, lows) for v in s):
            raise ValueError("candles must contain finite positive OHLC prices")

        latest = closes[-1]
        short_return = self._return_percent(closes[-self.short_window - 1], latest)
        long_return = self._return_percent(closes[-self.long_window - 1], latest)
        rsi = calculate_rsi(closes, self.rsi_period)[-1]
        fast_ema = calculate_ema(closes, self.fast_ema_period)[-1]
        slow_ema = calculate_ema(closes, self.slow_ema_period)[-1]
        _, _, macd_histogram = calculate_macd(closes, self.fast_ema_period, self.slow_ema_period, self.macd_signal_period)
        macd_hist = macd_histogram[-1]
        adx_values, plus_values, minus_values = calculate_adx(highs, lows, closes, self.adx_period)
        adx, plus_di, minus_di = adx_values[-1], plus_values[-1], minus_values[-1]

        evidence = []
        reasoning = [f"{self.name} timeframe: {self.timeframe}.", f"Short momentum: {short_return:.4f}%.", f"Long momentum: {long_return:.4f}%."]
        price_up = short_return > self.signal_threshold_percent and long_return > self.signal_threshold_percent
        price_down = short_return < -self.signal_threshold_percent and long_return < -self.signal_threshold_percent
        evidence.append(1.0 if price_up else -1.0 if price_down else 0.0)

        if rsi > 55:
            evidence.append(1.0); reasoning.append(f"RSI supports bullish momentum: {rsi:.2f}.")
        elif rsi < 45:
            evidence.append(-1.0); reasoning.append(f"RSI supports bearish momentum: {rsi:.2f}.")
        else:
            evidence.append(0.0); reasoning.append(f"RSI is neutral: {rsi:.2f}.")

        if macd_hist is not None:
            evidence.append(1.0 if macd_hist > 0 else -1.0 if macd_hist < 0 else 0.0)
            reasoning.append(f"MACD histogram: {macd_hist:.6f}.")
        if fast_ema is not None and slow_ema is not None:
            evidence.append(1.0 if fast_ema > slow_ema else -1.0 if fast_ema < slow_ema else 0.0)
            reasoning.append("EMA alignment is bullish." if fast_ema > slow_ema else "EMA alignment is bearish." if fast_ema < slow_ema else "EMA alignment is neutral.")
        if adx is not None and plus_di is not None and minus_di is not None:
            directional = 1.0 if plus_di > minus_di else -1.0 if minus_di > plus_di else 0.0
            evidence.append(directional if adx >= self.adx_threshold else 0.0)
            reasoning.append(f"ADX: {adx:.2f}; trend strength {'confirmed' if adx >= self.adx_threshold else 'not confirmed'}.")

        agreement = sum(evidence) / len(evidence)
        action = Action.BUY if agreement >= 0.60 else Action.SELL if agreement <= -0.60 else Action.HOLD
        strength = min(1.0, abs(agreement))
        score = round(50.0 + 50.0 * tanh(strength * 2.0), 4)
        confidence = round(50.0 + 40.0 * strength, 4)
        reasoning.append(f"Momentum indicator agreement: {agreement:.2f}.")
        reasoning.append("Momentum evidence is mixed; holding." if action is Action.HOLD else f"Momentum evidence aligns for {action.value}.")
        return AlgorithmSignal(algorithm=self.name, symbol=symbol, timeframe=self.timeframe,
                               action=action, score=score, confidence=confidence,
                               expected_edge=None, reasoning=reasoning)

    @staticmethod
    def _return_percent(start: float, end: float) -> float:
        return ((end / start) - 1.0) * 100.0
