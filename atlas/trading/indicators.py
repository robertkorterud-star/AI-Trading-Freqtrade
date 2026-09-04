"""
Trading Indicators

Technical indicators used by ATLAS backtesting.
"""


def calculate_rsi(
    closes: list[float],
    period: int = 14,
) -> list[float]:
    """Calculate RSI values."""

    if len(closes) < period + 1:
        return [50.0] * len(closes)

    rsi = [50.0] * len(closes)

    gains = []
    losses = []

    for index in range(1, len(closes)):

        change = closes[index] - closes[index - 1]

        gains.append(
            max(change, 0.0)
        )

        losses.append(
            max(-change, 0.0)
        )

    for index in range(period, len(closes)):

        average_gain = (
            sum(
                gains[index - period:index]
            )
            / period
        )

        average_loss = (
            sum(
                losses[index - period:index]
            )
            / period
        )

        if average_loss == 0:
            rsi[index] = 100.0
            continue

        relative_strength = (
            average_gain / average_loss
        )

        rsi[index] = (
            100
            - (
                100
                / (1 + relative_strength)
            )
        )

    return rsi


def calculate_sma(
    values: list[float],
    period: int = 20,
) -> list[float | None]:
    """Calculate SMA using only complete historical windows."""

    if period <= 0:
        raise ValueError("period must be greater than zero.")

    if not values:
        return []

    sma = []

    for index in range(len(values)):

        if index + 1 < period:
            sma.append(None)
            continue

        window = values[
            index - period + 1:index + 1
        ]

        sma.append(
            sum(window) / period
        )

    return sma


def calculate_ema(
    values: list[float],
    period: int = 20,
) -> list[float | None]:
    """Calculate EMA values with an SMA seed."""

    if period <= 0:
        raise ValueError("period must be greater than zero.")

    if not values:
        return []

    result: list[float | None] = [None] * len(values)
    if len(values) < period:
        return result

    current = sum(values[:period]) / period
    result[period - 1] = current
    multiplier = 2.0 / (period + 1)

    for index in range(period, len(values)):
        current = (values[index] - current) * multiplier + current
        result[index] = current

    return result


def calculate_macd(
    closes: list[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """Calculate MACD line, signal line and histogram."""

    if fast_period <= 0 or slow_period <= 0 or signal_period <= 0:
        raise ValueError("indicator periods must be greater than zero.")
    if fast_period >= slow_period:
        raise ValueError("fast_period must be smaller than slow_period.")

    fast = calculate_ema(closes, fast_period)
    slow = calculate_ema(closes, slow_period)
    line: list[float | None] = [None] * len(closes)

    for index in range(len(closes)):
        if fast[index] is not None and slow[index] is not None:
            line[index] = fast[index] - slow[index]

    available = [value for value in line if value is not None]
    signal_values = calculate_ema(available, signal_period)
    signal: list[float | None] = [None] * len(closes)
    available_index = 0
    for index, value in enumerate(line):
        if value is not None:
            signal[index] = signal_values[available_index]
            available_index += 1

    histogram: list[float | None] = [None] * len(closes)
    for index in range(len(closes)):
        if line[index] is not None and signal[index] is not None:
            histogram[index] = line[index] - signal[index]

    return line, signal, histogram


def calculate_adx(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 14,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """Calculate ADX, +DI and -DI using Wilder smoothing."""

    if period <= 0:
        raise ValueError("period must be greater than zero.")
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("highs, lows and closes must have equal length.")

    length = len(closes)
    adx_values: list[float | None] = [None] * length
    plus_di: list[float | None] = [None] * length
    minus_di: list[float | None] = [None] * length
    if length <= period * 2:
        return adx_values, plus_di, minus_di

    true_ranges: list[float] = []
    plus_moves: list[float] = []
    minus_moves: list[float] = []

    for index in range(1, length):
        up_move = highs[index] - highs[index - 1]
        down_move = lows[index - 1] - lows[index]
        plus_moves.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_moves.append(down_move if down_move > up_move and down_move > 0 else 0.0)
        true_ranges.append(
            max(
                highs[index] - lows[index],
                abs(highs[index] - closes[index - 1]),
                abs(lows[index] - closes[index - 1]),
            )
        )

    smoothed_tr = sum(true_ranges[:period])
    smoothed_plus = sum(plus_moves[:period])
    smoothed_minus = sum(minus_moves[:period])
    dx: list[float | None] = [None] * length

    for offset in range(period - 1, len(true_ranges)):
        if offset > period - 1:
            smoothed_tr = smoothed_tr - smoothed_tr / period + true_ranges[offset]
            smoothed_plus = smoothed_plus - smoothed_plus / period + plus_moves[offset]
            smoothed_minus = smoothed_minus - smoothed_minus / period + minus_moves[offset]

        index = offset + 1
        if smoothed_tr == 0:
            current_plus = current_minus = current_dx = 0.0
        else:
            current_plus = 100.0 * smoothed_plus / smoothed_tr
            current_minus = 100.0 * smoothed_minus / smoothed_tr
            denominator = current_plus + current_minus
            current_dx = (
                100.0 * abs(current_plus - current_minus) / denominator
                if denominator
                else 0.0
            )

        plus_di[index] = current_plus
        minus_di[index] = current_minus
        dx[index] = current_dx

    first_adx_index = period * 2 - 1
    initial_dx = [value for value in dx[period:first_adx_index + 1] if value is not None]
    if len(initial_dx) < period:
        return adx_values, plus_di, minus_di

    current_adx = sum(initial_dx) / period
    adx_values[first_adx_index] = current_adx
    for index in range(first_adx_index + 1, length):
        if dx[index] is not None:
            current_adx = ((current_adx * (period - 1)) + dx[index]) / period
            adx_values[index] = current_adx

    return adx_values, plus_di, minus_di
