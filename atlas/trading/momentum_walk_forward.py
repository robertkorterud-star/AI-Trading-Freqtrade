"""
ATLAS Momentum Walk-Forward.

Research-only walk-forward evaluation for the
Momentum strategy.
"""

from dataclasses import dataclass

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
)
from atlas.trading.momentum_backtest import (
    MomentumBacktester,
)


@dataclass(frozen=True, slots=True)
class MomentumWalkForwardWindow:
    train_start: int
    train_end: int
    test_start: int
    test_end: int

    strategy_return_percent: float
    buy_and_hold_return_percent: float


@dataclass(frozen=True, slots=True)
class MomentumWalkForwardResult:
    windows: tuple[
        MomentumWalkForwardWindow,
        ...
    ]

    total_strategy_return_percent: float
    total_buy_and_hold_return_percent: float

    positive_windows: int
    negative_windows: int


class MomentumWalkForward:
    """Evaluate momentum using rolling walk-forward windows."""

    def __init__(
        self,
        lookback_period: int = 20,
        transaction_cost_percent: float = 0.1,
        slippage_percent: float = 0.05,
    ):
        self.lookback_period = lookback_period
        self.transaction_cost_percent = (
            transaction_cost_percent
        )
        self.slippage_percent = (
            slippage_percent
        )

    def evaluate(
        self,
        data: HistoricalMarketData,
        *,
        train_size: int,
        test_size: int,
    ) -> MomentumWalkForwardResult:

        if train_size <= 0:
            raise ValueError(
                "train_size must be positive."
            )

        if test_size <= 0:
            raise ValueError(
                "test_size must be positive."
            )

        closes = data.closes

        windows = []

        start = 0

        while (
            start
            + train_size
            + test_size
            <= len(closes)
        ):

            train_end = (
                start
                + train_size
            )

            test_start = train_end

            test_end = (
                test_start
                + test_size
            )

            test_bars = list(
                data.bars[
                    test_start:test_end
                ]
            )

            if len(test_bars) < test_size:
                break

            test_data = HistoricalMarketData(
                symbol=data.symbol,
                timeframe=data.timeframe,
                source=data.source,
                bars=test_bars,
            )

            result = MomentumBacktester(
                lookback_period=(
                    self.lookback_period
                ),
                transaction_cost_percent=(
                    self.transaction_cost_percent
                ),
                slippage_percent=(
                    self.slippage_percent
                ),
            ).run(test_data)

            windows.append(
                MomentumWalkForwardWindow(
                    train_start=start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_end,
                    strategy_return_percent=(
                        result.strategy_return_percent
                    ),
                    buy_and_hold_return_percent=(
                        result.buy_and_hold_return_percent
                    ),
                )
            )

            start += test_size

        total_strategy_return = sum(
            window.strategy_return_percent
            for window in windows
        )

        total_buy_and_hold_return = sum(
            window.buy_and_hold_return_percent
            for window in windows
        )

        positive_windows = sum(
            window.strategy_return_percent > 0.0
            for window in windows
        )

        negative_windows = sum(
            window.strategy_return_percent <= 0.0
            for window in windows
        )

        return MomentumWalkForwardResult(
            windows=tuple(windows),
            total_strategy_return_percent=(
                total_strategy_return
            ),
            total_buy_and_hold_return_percent=(
                total_buy_and_hold_return
            ),
            positive_windows=positive_windows,
            negative_windows=negative_windows,
        )
