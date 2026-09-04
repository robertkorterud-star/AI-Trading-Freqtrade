"""Pure, dependency-free technical indicator calculations for ATLAS."""

from collections.abc import Sequence


def _validate_period(period: int) -> None:
    if period <= 0:
        raise ValueError("period must be greater than zero")


def _validate_series(values: Sequence[float], minimum: int = 1) -> None:
    if len(values) < minimum:
        raise ValueError(f"Need at least {minimum} observations, got {len(values)}")


def ema(values: Sequence[float], period: int) -> float:
    """Return the latest exponential moving average using an SMA seed."""
    _validate_period(period)
    _validate_series(values, period)
    seed = sum(values[:period]) / period
    multiplier = 2.0 / (period + 1)
    result = seed
    for value in values[period:]:
        result = (value - result) * multiplier + result
    return float(result)


def rsi(closes: Sequence[float], period: int = 14) -> float:
    """Return Wilder's latest RSI in the range 0..100."""
    _validate_period(period)
    _validate_series(closes, period + 1)
    gains = [max(closes[i] - closes[i - 1], 0.0) for i in range(1, len(closes))]
    losses = [max(closes[i - 1] - closes[i], 0.0) for i in range(1, len(closes))]
    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period
    for gain, loss in zip(gains[period:], losses[period:]):
        average_gain = ((average_gain * (period - 1)) + gain) / period
        average_loss = ((average_loss * (period - 1)) + loss) / period
    if average_loss == 0:
        return 100.0 if average_gain > 0 else 50.0
    relative_strength = average_gain / average_loss
    return float(100.0 - (100.0 / (1.0 + relative_strength)))


def macd(
    closes: Sequence[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[float, float, float]:
    """Return latest MACD line, signal line and histogram."""
    _validate_period(fast_period)
    _validate_period(slow_period)
    _validate_period(signal_period)
    if fast_period >= slow_period:
        raise ValueError("fast_period must be smaller than slow_period")
    _validate_series(closes, slow_period + signal_period - 1)

    fast_alpha = 2.0 / (fast_period + 1)
    slow_alpha = 2.0 / (slow_period + 1)
    fast = sum(closes[:fast_period]) / fast_period
    slow = sum(closes[:slow_period]) / slow_period
    macd_values: list[float] = []
    for index, value in enumerate(closes[slow_period:], start=slow_period):
        fast = (value - fast) * fast_alpha + fast
        slow = (value - slow) * slow_alpha + slow
        macd_values.append(fast - slow)
    # Include the first slow-period MACD point from the seeded averages.
    macd_values.insert(0, sum(closes[:fast_period]) / fast_period - slow)
    if len(macd_values) < signal_period:
        raise ValueError("Insufficient data for MACD signal line")
    signal = ema(macd_values, signal_period)
    line = macd_values[-1]
    return float(line), float(signal), float(line - signal)


def adx(
    candles: Sequence[object],
    period: int = 14,
) -> tuple[float, float, float]:
    """Return latest ADX, +DI and -DI using Wilder smoothing.

    Candles must expose ``high``, ``low`` and ``close`` attributes. Keeping
    this function structural lets the indicator layer operate on ATLAS's
    normalized candle model without coupling it to a data provider.
    """
    _validate_period(period)
    _validate_series(candles, period * 2)
    true_ranges: list[float] = []
    plus_moves: list[float] = []
    minus_moves: list[float] = []
    for previous, current in zip(candles, candles[1:]):
        up_move = current.high - previous.high
        down_move = previous.low - current.low
        plus_moves.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_moves.append(down_move if down_move > up_move and down_move > 0 else 0.0)
        true_ranges.append(
            max(current.high - current.low, abs(current.high - previous.close), abs(current.low - previous.close))
        )

    tr = sum(true_ranges[:period])
    plus = sum(plus_moves[:period])
    minus = sum(minus_moves[:period])
    dx_values: list[float] = []

    def directional_values(tr_value: float, plus_value: float, minus_value: float) -> tuple[float, float, float]:
        if tr_value == 0:
            return 0.0, 0.0, 0.0
        plus_di = 100.0 * plus_value / tr_value
        minus_di = 100.0 * minus_value / tr_value
        denominator = plus_di + minus_di
        dx = 100.0 * abs(plus_di - minus_di) / denominator if denominator else 0.0
        return plus_di, minus_di, dx

    plus_di, minus_di, dx = directional_values(tr, plus, minus)
    dx_values.append(dx)
    for index in range(period, len(true_ranges)):
        tr = tr - (tr / period) + true_ranges[index]
        plus = plus - (plus / period) + plus_moves[index]
        minus = minus - (minus / period) + minus_moves[index]
        plus_di, minus_di, dx = directional_values(tr, plus, minus)
        dx_values.append(dx)

    if len(dx_values) < period:
        raise ValueError("Insufficient data for ADX")
    adx_value = sum(dx_values[:period]) / period
    for dx in dx_values[period:]:
        adx_value = ((adx_value * (period - 1)) + dx) / period
    return float(adx_value), float(plus_di), float(minus_di)
