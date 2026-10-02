"""
ATLAS Mean Reversion Backtest.

Research-only mean-reversion strategy.

The strategy enters when price moves sufficiently below
its moving average and exits when price returns toward
the moving average.
"""

from dataclasses import dataclass

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
)


@dataclass(frozen=True, slots=True)
class MeanReversionTrade:
    entry_index: int
    exit_index: int
    entry_price: float
    exit_price: float
    return_percent: float


@dataclass(frozen=True, slots=True)
class MeanReversionBacktestResult:
    strategy_return_percent: float
    buy_and_hold_return_percent: float
    max_drawdown_percent: float
    trade_count: int
    win_rate_percent: float
    trades: tuple[MeanReversionTrade, ...]


class MeanReversionBacktester:
    """Backtest a simple moving-average mean-reversion strategy."""

    def __init__(
        self,
        lookback_period: int = 20,
        entry_deviation_percent: float = 2.0,
        transaction_cost_percent: float = 0.1,
        slippage_percent: float = 0.05,
    ):
        if lookback_period <= 1:
            raise ValueError(
                "lookback_period must be greater than 1."
            )

        if entry_deviation_percent <= 0:
            raise ValueError(
                "entry_deviation_percent must be positive."
            )

        self.lookback_period = lookback_period
        self.entry_deviation_percent = entry_deviation_percent
        self.transaction_cost_percent = transaction_cost_percent
        self.slippage_percent = slippage_percent

    def run(
        self,
        data: HistoricalMarketData,
        *,
        evaluation_start_index: int = 0,
    ) -> MeanReversionBacktestResult:

        closes = data.closes

        if (
            evaluation_start_index < 0
            or evaluation_start_index > len(closes)
        ):
            raise ValueError(
                "evaluation_start_index must be between "
                "0 and len(data)."
            )

        if len(closes) <= self.lookback_period:
            return MeanReversionBacktestResult(
                strategy_return_percent=0.0,
                buy_and_hold_return_percent=0.0,
                max_drawdown_percent=0.0,
                trade_count=0,
                win_rate_percent=0.0,
                trades=(),
            )

        capital = 1.0
        equity = 1.0

        position = False
        entry_index = None
        entry_price = 0.0

        trade_returns = []
        trades = []
        equity_curve = [equity]

        cost_percent = (
            self.transaction_cost_percent
            + self.slippage_percent
        )

        for index in range(
            max(
                self.lookback_period,
                evaluation_start_index,
            ),
            len(closes),
        ):

            price = closes[index]

            window = closes[
                index - self.lookback_period:
                index
            ]

            moving_average = (
                sum(window)
                / len(window)
            )

            deviation_percent = (
                (price - moving_average)
                / moving_average
                * 100.0
            )

            if not position:

                if (
                    deviation_percent
                    <= -self.entry_deviation_percent
                ):
                    position = True
                    entry_index = index
                    entry_price = price

                    capital *= (
                        1.0
                        - cost_percent / 100.0
                    )

            else:

                if price >= moving_average:

                    trade_return = (
                        (price - entry_price)
                        / entry_price
                        * 100.0
                    )

                    capital *= (
                        1.0
                        + trade_return / 100.0
                    )

                    capital *= (
                        1.0
                        - cost_percent / 100.0
                    )

                    trade_returns.append(
                        trade_return
                    )

                    trades.append(
                        MeanReversionTrade(
                            entry_index=entry_index,
                            exit_index=index,
                            entry_price=entry_price,
                            exit_price=price,
                            return_percent=trade_return,
                        )
                    )

                    position = False
                    entry_index = None
                    entry_price = 0.0

            equity = capital

            if position:
                equity = (
                    capital
                    * price
                    / entry_price
                )

            equity_curve.append(equity)

        if position:
            final_index = len(closes) - 1
            final_price = closes[final_index]

            trade_return = (
                (final_price - entry_price)
                / entry_price
                * 100.0
            )

            capital *= (
                1.0
                + trade_return / 100.0
            )

            capital *= (
                1.0
                - cost_percent / 100.0
            )

            trade_returns.append(
                trade_return
            )

            trades.append(
                MeanReversionTrade(
                    entry_index=entry_index,
                    exit_index=final_index,
                    entry_price=entry_price,
                    exit_price=final_price,
                    return_percent=trade_return,
                )
            )

            equity = capital
            equity_curve.append(equity)

        strategy_return = (
            capital - 1.0
        ) * 100.0

        benchmark_start = max(
            evaluation_start_index,
            0,
        )

        buy_and_hold = (
            (
                closes[-1]
                - closes[benchmark_start]
            )
            / closes[benchmark_start]
            * 100.0
            if benchmark_start < len(closes)
            else 0.0
        )

        peak = equity_curve[0]
        max_drawdown = 0.0

        for value in equity_curve:

            peak = max(
                peak,
                value,
            )

            drawdown = (
                (value - peak)
                / peak
                * 100.0
            )

            max_drawdown = min(
                max_drawdown,
                drawdown,
            )

        trade_count = len(
            trade_returns
        )

        win_rate = (
            sum(
                value > 0
                for value in trade_returns
            )
            / trade_count
            * 100.0
            if trade_count
            else 0.0
        )

        return MeanReversionBacktestResult(
            strategy_return_percent=(
                strategy_return
            ),
            buy_and_hold_return_percent=(
                buy_and_hold
            ),
            max_drawdown_percent=(
                max_drawdown
            ),
            trade_count=trade_count,
            win_rate_percent=win_rate,
            trades=tuple(trades),
        )
