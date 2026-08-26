"""
ATLAS Trend Following Backtest Engine.

Research-only backtesting for the Trend Following strategy.

This module does not create live trading decisions.
"""

from dataclasses import dataclass

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
)

from atlas.trading.trend_following import (
    TrendFollowingAnalyzer,
)


@dataclass(frozen=True, slots=True)
class TrendTrade:
    entry_index: int
    exit_index: int
    entry_price: float
    exit_price: float
    return_percent: float


@dataclass(frozen=True, slots=True)
class TrendFollowingBacktestResult:
    initial_capital: float
    final_capital: float
    strategy_return_percent: float
    buy_and_hold_return_percent: float
    max_drawdown_percent: float
    trade_count: int
    winning_trades: int
    losing_trades: int
    win_rate_percent: float
    transaction_cost_percent: float
    slippage_percent: float
    trades: tuple[TrendTrade, ...]


class TrendFollowingBacktester:
    """
    Backtests the TrendFollowingAnalyzer.

    Signals are calculated using candles available at the
    current index only. Orders are executed on the next
    candle's close to avoid look-ahead bias.
    """

    def __init__(
        self,
        fast_period: int = 10,
        slow_period: int = 30,
        transaction_cost_percent: float = 0.10,
        slippage_percent: float = 0.05,
    ):
        if transaction_cost_percent < 0:
            raise ValueError(
                "transaction_cost_percent cannot be negative."
            )

        if slippage_percent < 0:
            raise ValueError(
                "slippage_percent cannot be negative."
            )

        self.analyzer = TrendFollowingAnalyzer(
            fast_period=fast_period,
            slow_period=slow_period,
        )

        self.transaction_cost_percent = (
            float(transaction_cost_percent)
        )

        self.slippage_percent = (
            float(slippage_percent)
        )

    def run(
        self,
        closes: list[float] | HistoricalMarketData,
        initial_capital: float = 10000.0,
    ) -> TrendFollowingBacktestResult:

        if isinstance(closes, HistoricalMarketData):
            prices = closes.closes
        else:
            prices = [
                float(price)
                for price in closes
            ]

        if initial_capital <= 0:
            raise ValueError(
                "initial_capital must be positive."
            )

        if len(prices) < 2:
            return self._empty_result(
                initial_capital
            )

        if any(price <= 0 for price in prices):
            raise ValueError(
                "All prices must be positive."
            )

        capital = float(initial_capital)
        equity_curve = [capital]

        in_position = False
        entry_index = None
        entry_price = None

        trades: list[TrendTrade] = []

        for index in range(
            len(prices) - 1
        ):
            historical_prices = prices[
                : index + 1
            ]

            result = self.analyzer.analyze(
                historical_prices
            )

            if result.signal == "BULLISH":
                desired_position = True
            elif result.signal == "BEARISH":
                desired_position = False
            else:
                desired_position = in_position

            if (
                desired_position
                and not in_position
            ):
                execution_index = index + 1
                execution_price = self._buy_price(
                    prices[execution_index]
                )

                in_position = True
                entry_index = execution_index
                entry_price = execution_price

            elif (
                not desired_position
                and in_position
            ):
                execution_index = index + 1
                execution_price = self._sell_price(
                    prices[execution_index]
                )

                trade = self._close_trade(
                    entry_index=entry_index,
                    exit_index=execution_index,
                    entry_price=entry_price,
                    exit_price=execution_price,
                )

                trades.append(trade)

                capital *= (
                    1.0
                    + trade.return_percent / 100.0
                )

                in_position = False
                entry_index = None
                entry_price = None

            if in_position:
                mark_to_market = (
                    self._sell_price(
                        prices[index]
                    )
                )

                if entry_price:
                    unrealized = (
                        mark_to_market
                        / entry_price
                        - 1.0
                    )

                    equity_curve.append(
                        capital
                        * (
                            1.0
                            + unrealized
                        )
                    )
            else:
                equity_curve.append(
                    capital
                )

        # Close an open position at the final price.
        if in_position:
            execution_index = (
                len(prices) - 1
            )

            execution_price = self._sell_price(
                prices[execution_index]
            )

            trade = self._close_trade(
                entry_index=entry_index,
                exit_index=execution_index,
                entry_price=entry_price,
                exit_price=execution_price,
            )

            trades.append(trade)

            capital *= (
                1.0
                + trade.return_percent / 100.0
            )

        final_capital = capital

        strategy_return = (
            (
                final_capital
                / initial_capital
            )
            - 1.0
        ) * 100.0

        buy_and_hold = (
            (
                prices[-1]
                / prices[0]
            )
            - 1.0
        ) * 100.0

        max_drawdown = (
            self._max_drawdown_percent(
                equity_curve
            )
        )

        winning = sum(
            trade.return_percent > 0
            for trade in trades
        )

        losing = sum(
            trade.return_percent <= 0
            for trade in trades
        )

        trade_count = len(trades)

        win_rate = (
            winning
            / trade_count
            * 100.0
            if trade_count
            else 0.0
        )

        return TrendFollowingBacktestResult(
            initial_capital=initial_capital,
            final_capital=final_capital,
            strategy_return_percent=strategy_return,
            buy_and_hold_return_percent=buy_and_hold,
            max_drawdown_percent=max_drawdown,
            trade_count=trade_count,
            winning_trades=winning,
            losing_trades=losing,
            win_rate_percent=win_rate,
            transaction_cost_percent=(
                self.transaction_cost_percent
            ),
            slippage_percent=(
                self.slippage_percent
            ),
            trades=tuple(trades),
        )

    def _buy_price(
        self,
        price: float,
    ) -> float:
        return price * (
            1.0
            + (
                self.slippage_percent
                / 100.0
            )
            + (
                self.transaction_cost_percent
                / 100.0
            )
        )

    def _sell_price(
        self,
        price: float,
    ) -> float:
        return price * (
            1.0
            - (
                self.slippage_percent
                / 100.0
            )
            - (
                self.transaction_cost_percent
                / 100.0
            )
        )

    def _close_trade(
        self,
        *,
        entry_index: int,
        exit_index: int,
        entry_price: float,
        exit_price: float,
    ) -> TrendTrade:

        return_percent = (
            (
                exit_price
                / entry_price
            )
            - 1.0
        ) * 100.0

        return TrendTrade(
            entry_index=entry_index,
            exit_index=exit_index,
            entry_price=entry_price,
            exit_price=exit_price,
            return_percent=return_percent,
        )

    @staticmethod
    def _max_drawdown_percent(
        equity_curve: list[float],
    ) -> float:

        if not equity_curve:
            return 0.0

        peak = equity_curve[0]
        max_drawdown = 0.0

        for equity in equity_curve:
            if equity > peak:
                peak = equity

            if peak <= 0:
                continue

            drawdown = (
                (
                    equity
                    / peak
                )
                - 1.0
            ) * 100.0

            if drawdown < max_drawdown:
                max_drawdown = drawdown

        return max_drawdown

    @staticmethod
    def _empty_result(
        initial_capital: float,
    ) -> TrendFollowingBacktestResult:

        return TrendFollowingBacktestResult(
            initial_capital=initial_capital,
            final_capital=initial_capital,
            strategy_return_percent=0.0,
            buy_and_hold_return_percent=0.0,
            max_drawdown_percent=0.0,
            trade_count=0,
            winning_trades=0,
            losing_trades=0,
            win_rate_percent=0.0,
            transaction_cost_percent=0.0,
            slippage_percent=0.0,
            trades=(),
        )
