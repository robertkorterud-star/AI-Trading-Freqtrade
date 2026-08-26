"""
ATLAS Indicator Engine.

Calculates normalized technical-analysis features from OHLCV data.

This module does not generate trades. It produces features that can
later be consumed by market-regime analysis, multi-timeframe analysis,
strategy research and the ATLAS decision engine.
"""

from dataclasses import dataclass
from math import sqrt


@dataclass(slots=True)
class IndicatorSnapshot:
    close: float

    sma20: float | None
    sma50: float | None
    sma200: float | None

    ema20: float | None
    ema50: float | None

    rsi14: float | None

    macd: float | None
    macd_signal: float | None
    macd_histogram: float | None

    adx14: float | None

    atr14: float | None
    atr_percent: float | None

    bollinger_middle: float | None
    bollinger_upper: float | None
    bollinger_lower: float | None
    bollinger_width: float | None
    bollinger_position: float | None

    obv: float | None
    relative_volume: float | None

    breakout20: bool
    breakout50: bool

    data_quality: str


class IndicatorEngine:
    """Calculate technical-analysis features from OHLCV candles."""

    def calculate(
        self,
        candles: list[dict],
    ) -> IndicatorSnapshot:

        closes = [
            float(candle["close"])
            for candle in candles
        ]

        highs = [
            float(candle["high"])
            for candle in candles
        ]

        lows = [
            float(candle["low"])
            for candle in candles
        ]

        volumes = [
            float(candle.get("volume", 0.0))
            for candle in candles
        ]

        if not closes:
            return self._empty_snapshot()

        close = closes[-1]

        sma20 = self._sma(closes, 20)
        sma50 = self._sma(closes, 50)
        sma200 = self._sma(closes, 200)

        ema20 = self._ema(closes, 20)
        ema50 = self._ema(closes, 50)

        rsi14 = self._rsi(closes, 14)

        macd, macd_signal, macd_histogram = self._macd(
            closes
        )

        atr14 = self._atr(
            highs,
            lows,
            closes,
            14,
        )

        atr_percent = (
            (atr14 / close) * 100
            if atr14 is not None and close
            else None
        )

        (
            bollinger_middle,
            bollinger_upper,
            bollinger_lower,
            bollinger_width,
            bollinger_position,
        ) = self._bollinger(closes, 20, 2.0)

        obv = self._obv(
            closes,
            volumes,
        )

        relative_volume = self._relative_volume(
            volumes,
            20,
        )

        breakout20 = self._breakout(
            highs,
            close,
            20,
        )

        breakout50 = self._breakout(
            highs,
            close,
            50,
        )

        adx14 = self._adx(
            highs,
            lows,
            closes,
            14,
        )

        return IndicatorSnapshot(
            close=close,
            sma20=sma20,
            sma50=sma50,
            sma200=sma200,
            ema20=ema20,
            ema50=ema50,
            rsi14=rsi14,
            macd=macd,
            macd_signal=macd_signal,
            macd_histogram=macd_histogram,
            adx14=adx14,
            atr14=atr14,
            atr_percent=atr_percent,
            bollinger_middle=bollinger_middle,
            bollinger_upper=bollinger_upper,
            bollinger_lower=bollinger_lower,
            bollinger_width=bollinger_width,
            bollinger_position=bollinger_position,
            obv=obv,
            relative_volume=relative_volume,
            breakout20=breakout20,
            breakout50=breakout50,
            data_quality=self._data_quality(
                len(closes)
            ),
        )

    @staticmethod
    def _empty_snapshot() -> IndicatorSnapshot:
        return IndicatorSnapshot(
            close=0.0,
            sma20=None,
            sma50=None,
            sma200=None,
            ema20=None,
            ema50=None,
            rsi14=None,
            macd=None,
            macd_signal=None,
            macd_histogram=None,
            adx14=None,
            atr14=None,
            atr_percent=None,
            bollinger_middle=None,
            bollinger_upper=None,
            bollinger_lower=None,
            bollinger_width=None,
            bollinger_position=None,
            obv=None,
            relative_volume=None,
            breakout20=False,
            breakout50=False,
            data_quality="MISSING",
        )

    @staticmethod
    def _data_quality(count: int) -> str:
        if count == 0:
            return "MISSING"

        if count < 50:
            return "POOR"

        if count < 200:
            return "PARTIAL"

        return "GOOD"

    @staticmethod
    def _sma(
        values: list[float],
        period: int,
    ) -> float | None:

        if len(values) < period:
            return None

        return sum(values[-period:]) / period

    @staticmethod
    def _ema(
        values: list[float],
        period: int,
    ) -> float | None:

        if len(values) < period:
            return None

        multiplier = 2 / (period + 1)

        ema = sum(values[:period]) / period

        for value in values[period:]:
            ema = (
                (value - ema) * multiplier
                + ema
            )

        return ema

    @staticmethod
    def _rsi(
        values: list[float],
        period: int,
    ) -> float | None:

        if len(values) <= period:
            return None

        gains = []
        losses = []

        for index in range(1, len(values)):
            change = (
                values[index]
                - values[index - 1]
            )

            gains.append(max(change, 0.0))
            losses.append(max(-change, 0.0))

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        for index in range(period, len(gains)):
            avg_gain = (
                (avg_gain * (period - 1))
                + gains[index]
            ) / period

            avg_loss = (
                (avg_loss * (period - 1))
                + losses[index]
            ) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss

        return 100.0 - (
            100.0 / (1.0 + rs)
        )

    @classmethod
    def _macd(
        cls,
        values: list[float],
    ) -> tuple[
        float | None,
        float | None,
        float | None,
    ]:

        ema12 = cls._ema(values, 12)
        ema26 = cls._ema(values, 26)

        if ema12 is None or ema26 is None:
            return None, None, None

        macd = ema12 - ema26

        # A complete historical MACD signal line requires
        # the MACD series. Keep the first implementation
        # deterministic and avoid look-ahead assumptions.
        macd_signal = None
        macd_histogram = None

        if len(values) >= 35:
            macd_values = []

            for index in range(26, len(values)):
                fast = cls._ema(
                    values[: index + 1],
                    12,
                )
                slow = cls._ema(
                    values[: index + 1],
                    26,
                )

                if fast is not None and slow is not None:
                    macd_values.append(
                        fast - slow
                    )

            if len(macd_values) >= 9:
                macd_signal = cls._ema(
                    macd_values,
                    9,
                )

                if macd_signal is not None:
                    macd_histogram = (
                        macd - macd_signal
                    )

        return (
            macd,
            macd_signal,
            macd_histogram,
        )

    @staticmethod
    def _atr(
        highs: list[float],
        lows: list[float],
        closes: list[float],
        period: int,
    ) -> float | None:

        if len(closes) <= period:
            return None

        true_ranges = []

        for index in range(1, len(closes)):
            true_range = max(
                highs[index] - lows[index],
                abs(
                    highs[index]
                    - closes[index - 1]
                ),
                abs(
                    lows[index]
                    - closes[index - 1]
                ),
            )

            true_ranges.append(true_range)

        if len(true_ranges) < period:
            return None

        return (
            sum(true_ranges[-period:])
            / period
        )

    @classmethod
    def _bollinger(
        cls,
        values: list[float],
        period: int,
        deviations: float,
    ) -> tuple[
        float | None,
        float | None,
        float | None,
        float | None,
        float | None,
    ]:

        if len(values) < period:
            return (
                None,
                None,
                None,
                None,
                None,
            )

        window = values[-period:]

        middle = sum(window) / period

        variance = sum(
            (value - middle) ** 2
            for value in window
        ) / period

        stddev = sqrt(variance)

        upper = middle + (
            deviations * stddev
        )

        lower = middle - (
            deviations * stddev
        )

        width = (
            ((upper - lower) / middle) * 100
            if middle
            else None
        )

        if upper == lower:
            position = 0.5
        else:
            position = (
                (values[-1] - lower)
                / (upper - lower)
            )

        return (
            middle,
            upper,
            lower,
            width,
            position,
        )

    @staticmethod
    def _obv(
        closes: list[float],
        volumes: list[float],
    ) -> float | None:

        if not closes:
            return None

        obv = 0.0

        for index in range(1, len(closes)):
            if closes[index] > closes[index - 1]:
                obv += volumes[index]
            elif closes[index] < closes[index - 1]:
                obv -= volumes[index]

        return obv

    @staticmethod
    def _relative_volume(
        volumes: list[float],
        period: int,
    ) -> float | None:

        if len(volumes) < period:
            return None

        average = (
            sum(volumes[-period:])
            / period
        )

        if average == 0:
            return None

        return volumes[-1] / average

    @staticmethod
    def _breakout(
        highs: list[float],
        close: float,
        period: int,
    ) -> bool:

        if len(highs) <= period:
            return False

        previous_high = max(
            highs[-period - 1:-1]
        )

        return close > previous_high

    @staticmethod
    def _adx(
        highs: list[float],
        lows: list[float],
        closes: list[float],
        period: int,
    ) -> float | None:

        if len(closes) <= period * 2:
            return None

        true_ranges = []
        plus_dm = []
        minus_dm = []

        for index in range(1, len(closes)):
            up_move = (
                highs[index]
                - highs[index - 1]
            )

            down_move = (
                lows[index - 1]
                - lows[index]
            )

            plus_dm.append(
                up_move
                if up_move > down_move
                and up_move > 0
                else 0.0
            )

            minus_dm.append(
                down_move
                if down_move > up_move
                and down_move > 0
                else 0.0
            )

            true_ranges.append(
                max(
                    highs[index] - lows[index],
                    abs(
                        highs[index]
                        - closes[index - 1]
                    ),
                    abs(
                        lows[index]
                        - closes[index - 1]
                    ),
                )
            )

        if len(true_ranges) < period:
            return None

        atr = (
            sum(true_ranges[:period])
            / period
        )

        smoothed_plus = (
            sum(plus_dm[:period])
            / period
        )

        smoothed_minus = (
            sum(minus_dm[:period])
            / period
        )

        dx_values = []

        for index in range(
            period,
            len(true_ranges),
        ):
            atr = (
                (
                    atr * (period - 1)
                )
                + true_ranges[index]
            ) / period

            smoothed_plus = (
                (
                    smoothed_plus
                    * (period - 1)
                )
                + plus_dm[index]
            ) / period

            smoothed_minus = (
                (
                    smoothed_minus
                    * (period - 1)
                )
                + minus_dm[index]
            ) / period

            if atr == 0:
                continue

            plus_di = (
                100.0
                * smoothed_plus
                / atr
            )

            minus_di = (
                100.0
                * smoothed_minus
                / atr
            )

            denominator = (
                plus_di + minus_di
            )

            if denominator == 0:
                continue

            dx_values.append(
                100.0
                * abs(
                    plus_di - minus_di
                )
                / denominator
            )

        if len(dx_values) < period:
            return None

        return (
            sum(dx_values[-period:])
            / period
        )
