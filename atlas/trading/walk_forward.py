"""
ATLAS Walk-Forward Research Layer.

Evaluates a strategy chronologically by repeatedly training/
calibrating on a historical window and testing on the following
unseen window.

This module is research-only.
"""

from dataclasses import dataclass

from atlas.trading.trend_following_backtest import (
    TrendFollowingBacktester,
)


@dataclass(frozen=True, slots=True)
class WalkForwardWindow:
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    test_return_percent: float
    buy_and_hold_return_percent: float
    trade_count: int


@dataclass(frozen=True, slots=True)
class WalkForwardResult:
    total_points: int
    train_size: int
    test_size: int
    step_size: int
    windows: tuple[WalkForwardWindow, ...]
    total_strategy_return_percent: float
    total_buy_and_hold_return_percent: float
    average_test_return_percent: float
    positive_windows: int
    negative_windows: int


class TrendFollowingWalkForward:
    """Walk-forward evaluator for Trend Following."""

    def __init__(
        self,
        fast_period: int = 10,
        slow_period: int = 30,
        transaction_cost_percent: float = 0.10,
        slippage_percent: float = 0.05,
    ):
        self.fast_period = fast_period
        self.slow_period = slow_period

        self.transaction_cost_percent = (
            transaction_cost_percent
        )

        self.slippage_percent = (
            slippage_percent
        )

    def evaluate(
        self,
        closes: list[float],
        train_size: int,
        test_size: int,
        step_size: int | None = None,
    ) -> WalkForwardResult:

        if train_size <= 0:
            raise ValueError(
                "train_size must be positive."
            )

        if test_size <= 0:
            raise ValueError(
                "test_size must be positive."
            )

        if step_size is None:
            step_size = test_size

        if step_size <= 0:
            raise ValueError(
                "step_size must be positive."
            )

        prices = [
            float(price)
            for price in closes
        ]

        if any(price <= 0 for price in prices):
            raise ValueError(
                "All prices must be positive."
            )

        if len(prices) < (
            train_size + test_size
        ):
            return WalkForwardResult(
                total_points=len(prices),
                train_size=train_size,
                test_size=test_size,
                step_size=step_size,
                windows=(),
                total_strategy_return_percent=0.0,
                total_buy_and_hold_return_percent=0.0,
                average_test_return_percent=0.0,
                positive_windows=0,
                negative_windows=0,
            )

        windows = []

        start = 0

        while (
            start + train_size + test_size
            <= len(prices)
        ):
            train_start = start
            train_end = (
                start + train_size
            )

            test_start = train_end
            test_end = (
                test_start + test_size
            )

            train_prices = prices[
                train_start:train_end
            ]

            test_prices = prices[
                test_start:test_end
            ]

            # The training window is intentionally passed
            # separately. The current Trend Following model
            # has fixed parameters, so the training data is
            # used only to establish the historical boundary.
            #
            # Future test prices never enter the training
            # window.
            _ = train_prices

            backtester = TrendFollowingBacktester(
                fast_period=self.fast_period,
                slow_period=self.slow_period,
                transaction_cost_percent=(
                    self.transaction_cost_percent
                ),
                slippage_percent=(
                    self.slippage_percent
                ),
            )

            result = backtester.run(
                test_prices
            )

            windows.append(
                WalkForwardWindow(
                    train_start=train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_end,
                    test_return_percent=(
                        result.strategy_return_percent
                    ),
                    buy_and_hold_return_percent=(
                        result.buy_and_hold_return_percent
                    ),
                    trade_count=(
                        result.trade_count
                    ),
                )
            )

            start += step_size

        strategy_returns = [
            window.test_return_percent
            for window in windows
        ]

        benchmark_returns = [
            window.buy_and_hold_return_percent
            for window in windows
        ]

        positive = sum(
            value > 0
            for value in strategy_returns
        )

        negative = sum(
            value < 0
            for value in strategy_returns
        )

        average = (
            sum(strategy_returns)
            / len(strategy_returns)
            if strategy_returns
            else 0.0
        )

        total_strategy = (
            self._compound_returns(
                strategy_returns
            )
        )

        total_benchmark = (
            self._compound_returns(
                benchmark_returns
            )
        )

        return WalkForwardResult(
            total_points=len(prices),
            train_size=train_size,
            test_size=test_size,
            step_size=step_size,
            windows=tuple(windows),
            total_strategy_return_percent=(
                total_strategy
            ),
            total_buy_and_hold_return_percent=(
                total_benchmark
            ),
            average_test_return_percent=average,
            positive_windows=positive,
            negative_windows=negative,
        )

    @staticmethod
    def _compound_returns(
        returns: list[float],
    ) -> float:

        capital = 1.0

        for value in returns:
            capital *= (
                1.0 + value / 100.0
            )

        return (
            capital - 1.0
        ) * 100.0
