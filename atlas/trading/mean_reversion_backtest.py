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
class MeanReversionBacktestResult:
    strategy_return_percent: float
    buy_and_hold_return_percent: float
    max_drawdown_percent: float
    trade_count: int
    win_rate_percent: float


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
        self.entry_deviation_percent = (
            entry_deviation_percent
        )
        self.transaction_cost_percent = (
            transaction_cost_percent
        )
        self.slippage_percent = (
            slippage_percent
        )

    def run(
        self,
        data: HistoricalMarketData,
    ) -> MeanReversionBacktestResult:

        closes = data.closes

        if len(closes) <= self.lookback_period:
            return MeanReversionBacktestResult(
                strategy_return_percent=0.0,
                buy_and_hold_return_percent=0.0,
                max_drawdown_percent=0.0,
                trade_count=0,
                win_rate_percent=0.0,
            )

        capital = 1.0
        equity = 1.0

        position = False
        entry_price = 0.0

        trade_returns = []
        equity_curve = [equity]

        cost_percent = (
            self.transaction_cost_percent
            + self.slippage_percent
        )

        for index in range(
            self.lookback_period,
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

                    position = False
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
            final_price = closes[-1]

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

            equity = capital
            equity_curve.append(equity)

        strategy_return = (
            capital - 1.0
        ) * 100.0

        buy_and_hold = (
            (closes[-1] - closes[0])
            / closes[0]
            * 100.0
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
        )
