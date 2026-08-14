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
