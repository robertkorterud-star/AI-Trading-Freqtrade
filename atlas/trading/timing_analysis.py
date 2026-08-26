"""
Historical Timing Analysis

Finds historical entry opportunities produced by a strategy
and measures the best subsequent price opportunity.

This is an opportunity analysis, not a tradable backtest.
It deliberately reports the best future price after a signal
and must not be interpreted as an executable strategy return.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class TimingOpportunity:
    strategy_name: str
    symbol: str
    signals: int
    best_entry_timestamp: str | None
    best_entry_price: float | None
    best_exit_timestamp: str | None
    best_exit_price: float | None
    best_return: float
    max_drawdown: float
    holding_candles: int


class TimingAnalyzer:
    """Find historical timing opportunities for strategies."""

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
                best_exit_timestamp=None,
                best_exit_price=None,
                best_return=0.0,
                max_drawdown=0.0,
                holding_candles=0,
            )

        candidates = []

        previous_ma20 = None
        previous_ma50 = None

        for index, candle in enumerate(candles):

            close = float(
                candle["close"]
            )

            rsi = float(
                candle.get("rsi", 50.0)
            )

            ma20 = candle.get("ma20")
            ma50 = candle.get("ma50")

            if ma20 is not None:
                ma20 = float(ma20)

            if ma50 is not None:
                ma50 = float(ma50)

            signal = False

            if (
                strategy.name
                == "RSI Oversold Reversal"
            ):
                signal = rsi < 30

            elif (
                strategy.name
                == "Moving Average Crossover"
            ):
                signal = (
                    previous_ma20 is not None
                    and previous_ma50 is not None
                    and ma20 is not None
                    and ma50 is not None
                    and previous_ma20 <= previous_ma50
                    and ma20 > ma50
                )

            if signal and index < len(candles) - 1:

                entry_timestamp = str(
                    candle.get(
                        "timestamp",
                        index,
                    )
                )

                future = candles[
                    index + 1:
                ]

                best_exit_index = None
                best_exit_price = None

                for offset, future_candle in enumerate(
                    future,
                    start=index + 1,
                ):

                    high = float(
                        future_candle["high"]
                    )

                    if (
                        best_exit_price is None
                        or high > best_exit_price
                    ):
                        best_exit_price = high
                        best_exit_index = offset

                if (
                    best_exit_price is not None
                    and best_exit_index is not None
                ):

                    best_return = (
                        (
                            best_exit_price -
                            close
                        ) /
                        close
                    ) * 100

                    path = candles[
                        index + 1:
                        best_exit_index + 1
                    ]

                    if path:
                        lowest_price = min(
                            float(
                                item["low"]
                            )
                            for item in path
                        )

                        max_drawdown = max(
                            0.0,
                            (
                                (
                                    lowest_price -
                                    close
                                ) /
                                close
                            ) * 100,
                        ) * -1
                    else:
                        max_drawdown = 0.0

                    candidates.append(
                        {
                            "entry_timestamp":
                                entry_timestamp,
                            "entry_price":
                                close,
                            "exit_timestamp":
                                str(
                                    candles[
                                        best_exit_index
                                    ].get(
                                        "timestamp",
                                        best_exit_index,
                                    )
                                ),
                            "exit_price":
                                best_exit_price,
                            "return":
                                best_return,
                            "drawdown":
                                max_drawdown,
                            "holding":
                                (
                                    best_exit_index -
                                    index
                                ),
                        }
                    )

            previous_ma20 = ma20
            previous_ma50 = ma50

        if not candidates:
            return TimingOpportunity(
                strategy_name=strategy.name,
                symbol=strategy.symbol,
                signals=0,
                best_entry_timestamp=None,
                best_entry_price=None,
                best_exit_timestamp=None,
                best_exit_price=None,
                best_return=0.0,
                max_drawdown=0.0,
                holding_candles=0,
            )

        best = max(
            candidates,
            key=lambda item: item["return"],
        )

        return TimingOpportunity(
            strategy_name=strategy.name,
            symbol=strategy.symbol,
            signals=len(candidates),
            best_entry_timestamp=best[
                "entry_timestamp"
            ],
            best_entry_price=round(
                best["entry_price"],
                8,
            ),
            best_exit_timestamp=best[
                "exit_timestamp"
            ],
            best_exit_price=round(
                best["exit_price"],
                8,
            ),
            best_return=round(
                best["return"],
                2,
            ),
            max_drawdown=round(
                best["drawdown"],
                2,
            ),
            holding_candles=best[
                "holding"
            ],
        )
