"""
ATLAS Momentum Backtest.

Research-only momentum strategy.

The strategy is long when price momentum over the
lookback period is positive and exits when momentum
turns non-positive.
"""

from dataclasses import dataclass

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
)


@dataclass(frozen=True, slots=True)
class MomentumBacktestResult:
    strategy_return_percent: float
    buy_and_hold_return_percent: float
    max_drawdown_percent: float
    trade_count: int
    win_rate_percent: float


class MomentumBacktester:
    """Backtest a simple long-only momentum strategy."""

    def __init__(
        self,
        lookback_period: int = 20,
        transaction_cost_percent: float = 0.1,
        slippage_percent: float = 0.05,
    ):
        if lookback_period <= 0:
            raise ValueError(
                "lookback_period must be positive."
            )

        self.lookback_period = lookback_period
        self.transaction_cost_percent = (
            transaction_cost_percent
        )
        self.slippage_percent = (
            slippage_percent
        )

    def run(
        self,
        data: HistoricalMarketData,
    ) -> MomentumBacktestResult:

        closes = data.closes

        if len(closes) <= self.lookback_period:
            return MomentumBacktestResult(
                strategy_return_percent=0.0,
                buy_and_hold_return_percent=0.0,
                max_drawdown_percent=0.0,
                trade_count=0,
                win_rate_percent=0.0,
            )

        capital = 1.0
        position = False
        entry_price = 0.0

        trade_returns = []
        equity_curve = [capital]

        cost_percent = (
            self.transaction_cost_percent
            + self.slippage_percent
        )

        for index in range(
            self.lookback_period,
            len(closes),
        ):

            price = closes[index]
            reference_price = closes[
                index - self.lookback_period
            ]

            momentum_percent = (
                (price - reference_price)
                / reference_price
                * 100.0
            )

            if not position:

                if momentum_percent > 0.0:

                    position = True
                    entry_price = price

                    capital *= (
                        1.0
                        - cost_percent / 100.0
                    )

            else:

                if momentum_percent <= 0.0:

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

            equity_curve.append(capital)

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

        return MomentumBacktestResult(
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
