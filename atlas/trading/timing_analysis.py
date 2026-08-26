"""
Historical Timing Analysis

Measures historical opportunity after a strategy signal using
fixed forward windows rather than the best price in the entire
remaining dataset.

This is an opportunity analysis, not an executable backtest.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class TimingOpportunity:
    strategy_name: str
    symbol: str
    signals: int

    best_entry_timestamp: str | None
    best_entry_price: float | None

    max_favorable_excursion: float
    max_adverse_excursion: float

    median_favorable_excursion: float
    median_adverse_excursion: float

    best_window: int | None
    holding_candles: int

    target_hit_5: float
    stop_hit_5: float
    target_hit_20: float
    stop_hit_20: float


class TimingAnalyzer:
    """Analyse realistic forward opportunities after signals."""

    WINDOWS = (5, 10, 20, 50)

    def _signal(
        self,
        strategy,
        index: int,
        candles: list[dict],
        previous_ma20,
        previous_ma50,
    ):
        candle = candles[index]

        rsi = float(
            candle.get("rsi", 50.0)
        )

        ma20 = candle.get("ma20")
        ma50 = candle.get("ma50")

        if ma20 is not None:
            ma20 = float(ma20)

        if ma50 is not None:
            ma50 = float(ma50)

        if (
            strategy.name ==
            "RSI Oversold Reversal"
        ):
            return rsi < 30, ma20, ma50

        if (
            strategy.name ==
            "Moving Average Crossover"
        ):
            signal = (
                previous_ma20 is not None
                and previous_ma50 is not None
                and ma20 is not None
                and ma50 is not None
                and previous_ma20 <= previous_ma50
                and ma20 > ma50
            )

            return signal, ma20, ma50

        return False, ma20, ma50

    @staticmethod
    def _median(values: list[float]) -> float:
        if not values:
            return 0.0

        values = sorted(values)
        middle = len(values) // 2

        if len(values) % 2:
            return values[middle]

        return (
            values[middle - 1] +
            values[middle]
        ) / 2

    def analyze(
        self,
        strategy,
        candles: list[dict],
    ) -> TimingOpportunity:

        if len(candles) < 2:
            return TimingOpportunity(
                strategy_name=strategy.name,
                symbol=strategy.symbol,
                signals=0,
                best_entry_timestamp=None,
                best_entry_price=None,
                max_favorable_excursion=0.0,
                max_adverse_excursion=0.0,
                median_favorable_excursion=0.0,
                median_adverse_excursion=0.0,
                best_window=None,
                holding_candles=0,
                target_hit_5=0.0,
                stop_hit_5=0.0,
                target_hit_20=0.0,
                stop_hit_20=0.0,
            )

        opportunities = []

        previous_ma20 = None
        previous_ma50 = None

        for index in range(len(candles) - 1):

            signal, ma20, ma50 = self._signal(
                strategy,
                index,
                candles,
                previous_ma20,
                previous_ma50,
            )

            if signal:

                entry = float(
                    candles[index]["close"]
                )

                future = candles[
                    index + 1:
                ]

                best = {
                    "entry_timestamp":
                        str(
                            candles[index].get(
                                "timestamp",
                                index,
                            )
                        ),
                    "entry_price": entry,
                    "mfe": 0.0,
                    "mae": 0.0,
                    "best_window": None,
                    "holding": 0,
                    "hit_5_target": False,
                    "hit_5_stop": False,
                    "hit_20_target": False,
                    "hit_20_stop": False,
                }

                for window in self.WINDOWS:

                    window_candles = candles[
                        index + 1:
                        min(
                            len(candles),
                            index + 1 + window,
                        )
                    ]

                    if not window_candles:
                        continue

                    highs = [
                        float(
                            item["high"]
                        )
                        for item in window_candles
                    ]

                    lows = [
                        float(
                            item["low"]
                        )
                        for item in window_candles
                    ]

                    mfe = (
                        (
                            max(highs) - entry
                        ) /
                        entry
                    ) * 100

                    mae = (
                        (
                            min(lows) - entry
                        ) /
                        entry
                    ) * 100

                    if (
                        mfe >
                        best["mfe"]
                    ):
                        best["mfe"] = mfe
                        best["best_window"] = window

                    best["mae"] = min(
                        best["mae"],
                        mae,
                    )

                    target = (
                        0.04
                        if window <= 5
                        else 0.06
                    )

                    stop = (
                        -0.02
                        if window <= 5
                        else -0.03
                    )

                    if (
                        mfe >= target * 100
                    ):
                        if window <= 5:
                            best[
                                "hit_5_target"
                            ] = True
                        if window <= 20:
                            best[
                                "hit_20_target"
                            ] = True

                    if (
                        mae <= stop * 100
                    ):
                        if window <= 5:
                            best[
                                "hit_5_stop"
                            ] = True
                        if window <= 20:
                            best[
                                "hit_20_stop"
                            ] = True

                opportunities.append(best)

            previous_ma20 = ma20
            previous_ma50 = ma50

        if not opportunities:
            return TimingOpportunity(
                strategy_name=strategy.name,
                symbol=strategy.symbol,
                signals=0,
                best_entry_timestamp=None,
                best_entry_price=None,
                max_favorable_excursion=0.0,
                max_adverse_excursion=0.0,
                median_favorable_excursion=0.0,
                median_adverse_excursion=0.0,
                best_window=None,
                holding_candles=0,
                target_hit_5=0.0,
                stop_hit_5=0.0,
                target_hit_20=0.0,
                stop_hit_20=0.0,
            )

        best = max(
            opportunities,
            key=lambda item: item["mfe"],
        )

        mfe_values = [
            item["mfe"]
            for item in opportunities
        ]

        mae_values = [
            item["mae"]
            for item in opportunities
        ]

        total = len(opportunities)

        return TimingOpportunity(
            strategy_name=strategy.name,
            symbol=strategy.symbol,
            signals=total,
            best_entry_timestamp=
                best["entry_timestamp"],
            best_entry_price=round(
                best["entry_price"],
                8,
            ),
            max_favorable_excursion=round(
                max(
                    item["mfe"]
                    for item in opportunities
                ),
                2,
            ),
            max_adverse_excursion=round(
                min(
                    item["mae"]
                    for item in opportunities
                ),
                2,
            ),
            median_favorable_excursion=round(
                self._median(
                    mfe_values
                ),
                2,
            ),
            median_adverse_excursion=round(
                self._median(
                    mae_values
                ),
                2,
            ),
            best_window=best["best_window"],
            holding_candles=best[
                "best_window"
            ] or 0,
            target_hit_5=round(
                sum(
                    item["hit_5_target"]
                    for item in opportunities
                ) / total * 100,
                2,
            ),
            stop_hit_5=round(
                sum(
                    item["hit_5_stop"]
                    for item in opportunities
                ) / total * 100,
                2,
            ),
            target_hit_20=round(
                sum(
                    item["hit_20_target"]
                    for item in opportunities
                ) / total * 100,
                2,
            ),
            stop_hit_20=round(
                sum(
                    item["hit_20_stop"]
                    for item in opportunities
                ) / total * 100,
                2,
            ),
        )
