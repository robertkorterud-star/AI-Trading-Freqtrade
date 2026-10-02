"""
ATLAS Momentum Backtest.

Research-only momentum strategy.

The strategy enters when recent momentum is positive
and exits when momentum turns non-positive.
"""

from dataclasses import dataclass

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
)


@dataclass(frozen=True, slots=True)
class MomentumTrade:
    entry_index: int
    exit_index: int
    entry_price: float
    exit_price: float
    return_percent: float


@dataclass(frozen=True, slots=True)
class MomentumBacktestResult:
    strategy_return_percent: float
    buy_and_hold_return_percent: float
    max_drawdown_percent: float
    trade_count: int
    win_rate_percent: float
    trades: tuple[MomentumTrade, ...]


class MomentumBacktester:
    """Backtest a simple price-momentum strategy."""

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

        if transaction_cost_percent < 0:
            raise ValueError(
                "transaction_cost_percent cannot be negative."
            )

        if slippage_percent < 0:
            raise ValueError(
                "slippage_percent cannot be negative."
            )

        self.lookback_period = lookback_period
        self.transaction_cost_percent = (
            float(transaction_cost_percent)
        )
        self.slippage_percent = (
            float(slippage_percent)
        )

    def run(
        self,
        data: HistoricalMarketData,
        *,
        evaluation_start_index: int = 0,
    ) -> MomentumBacktestResult:

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
            return MomentumBacktestResult(
                strategy_return_percent=0.0,
                buy_and_hold_return_percent=0.0,
                max_drawdown_percent=0.0,
                trade_count=0,
                win_rate_percent=0.0,
                trades=(),
            )

        capital = 1.0
        equity_curve = [capital]

        in_position = False
        entry_index = None
        entry_price = None

        trades: list[MomentumTrade] = []

        total_cost_percent = (
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

            momentum = (
                price
                / closes[
                    index - self.lookback_period
                ]
                - 1.0
            ) * 100.0

            if momentum > 0.0 and not in_position:

                in_position = True
                entry_index = index
                entry_price = price

                capital *= (
                    1.0
                    - total_cost_percent / 100.0
                )

            elif momentum <= 0.0 and in_position:

                exit_index = index
                exit_price = price

                trade_return = (
                    exit_price
                    / entry_price
                    - 1.0
                ) * 100.0

                capital *= (
                    1.0
                    + trade_return / 100.0
                )

                capital *= (
                    1.0
                    - total_cost_percent / 100.0
                )

                trades.append(
                    MomentumTrade(
                        entry_index=entry_index,
                        exit_index=exit_index,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        return_percent=trade_return,
                    )
                )

                in_position = False
                entry_index = None
                entry_price = None

            if in_position and entry_price is not None:

                equity = (
                    capital
                    * price
                    / entry_price
                )

                equity_curve.append(equity)

            else:
                equity_curve.append(capital)

        if in_position:

            exit_index = len(closes) - 1
            exit_price = closes[exit_index]

            trade_return = (
                exit_price
                / entry_price
                - 1.0
            ) * 100.0

            capital *= (
                1.0
                + trade_return / 100.0
            )

            capital *= (
                1.0
                - total_cost_percent / 100.0
            )

            trades.append(
                MomentumTrade(
                    entry_index=entry_index,
                    exit_index=exit_index,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    return_percent=trade_return,
                )
            )

            equity_curve.append(capital)

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
                / closes[benchmark_start]
                - 1.0
            )
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

        trade_count = len(trades)

        winning_trades = sum(
            trade.return_percent > 0.0
            for trade in trades
        )

        win_rate = (
            winning_trades
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
            trades=tuple(trades),
        )
