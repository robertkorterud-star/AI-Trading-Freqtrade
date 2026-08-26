"""
ATLAS Trend Following Research Layer.

Produces descriptive trend-following evidence only.
It does not create BUY/SELL decisions.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TrendFollowingResult:
    signal: str
    fast_period: int
    slow_period: int
    fast_average: float | None
    slow_average: float | None
    trend_strength: float
    data_quality: str


class TrendFollowingAnalyzer:
    """Simple moving-average trend-following research model."""

    def __init__(
        self,
        fast_period: int = 10,
        slow_period: int = 30,
    ):
        if fast_period <= 0:
            raise ValueError(
                "fast_period must be positive."
            )

        if slow_period <= fast_period:
            raise ValueError(
                "slow_period must be greater than fast_period."
            )

        self.fast_period = fast_period
        self.slow_period = slow_period

    def analyze(
        self,
        closes: list[float],
    ) -> TrendFollowingResult:

        values = [
            float(value)
            for value in closes
        ]

        if not values:
            return self._missing()

        if len(values) < self.fast_period:
            return TrendFollowingResult(
                signal="UNKNOWN",
                fast_period=self.fast_period,
                slow_period=self.slow_period,
                fast_average=None,
                slow_average=None,
                trend_strength=0.0,
                data_quality="MISSING",
            )

        fast = self._sma(
            values[-self.fast_period:]
        )

        if len(values) < self.slow_period:
            return TrendFollowingResult(
                signal="UNKNOWN",
                fast_period=self.fast_period,
                slow_period=self.slow_period,
                fast_average=fast,
                slow_average=None,
                trend_strength=0.0,
                data_quality="PARTIAL",
            )

        slow = self._sma(
            values[-self.slow_period:]
        )

        if slow == 0:
            strength = 0.0
        else:
            strength = (
                (fast - slow)
                / abs(slow)
                * 100.0
            )

        if fast > slow:
            signal = "BULLISH"
        elif fast < slow:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"

        return TrendFollowingResult(
            signal=signal,
            fast_period=self.fast_period,
            slow_period=self.slow_period,
            fast_average=fast,
            slow_average=slow,
            trend_strength=strength,
            data_quality="GOOD",
        )

    @staticmethod
    def _sma(
        values: list[float],
    ) -> float:
        return sum(values) / len(values)

    def _missing(self) -> TrendFollowingResult:
        return TrendFollowingResult(
            signal="UNKNOWN",
            fast_period=self.fast_period,
            slow_period=self.slow_period,
            fast_average=None,
            slow_average=None,
            trend_strength=0.0,
            data_quality="MISSING",
        )
