"""
ATLAS Strategy Parameter Research.

Research-only parameter sweep for Trend Following.

Parameters are evaluated using walk-forward performance.
No live trading decisions are created.
"""

from dataclasses import dataclass

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
)
from atlas.trading.trend_following_backtest import (
    TrendFollowingBacktester,
)
from atlas.trading.walk_forward import (
    TrendFollowingWalkForward,
)


@dataclass(frozen=True, slots=True)
class StrategyParameterResult:
    fast_period: int
    slow_period: int

    backtest_return_percent: float
    backtest_buy_and_hold_percent: float
    max_drawdown_percent: float
    trade_count: int

    walk_forward_return_percent: float
    walk_forward_buy_and_hold_percent: float
    positive_windows: int
    negative_windows: int
    total_windows: int

    outperformed_walk_forward: bool


@dataclass(frozen=True, slots=True)
class StrategyParameterResearchResult:
    results: tuple[StrategyParameterResult, ...]

    @property
    def best(self) -> StrategyParameterResult | None:
        if not self.results:
            return None

        return max(
            self.results,
            key=lambda result: (
                result.walk_forward_return_percent
                - result.walk_forward_buy_and_hold_percent,
                result.positive_windows
                - result.negative_windows,
                -result.max_drawdown_percent,
            ),
        )


class StrategyParameterResearch:
    """Evaluate multiple Trend Following parameter sets."""

    def __init__(
        self,
        transaction_cost_percent: float = 0.1,
        slippage_percent: float = 0.05,
    ):
        self.transaction_cost_percent = (
            transaction_cost_percent
        )
        self.slippage_percent = (
            slippage_percent
        )

    def run(
        self,
        data: HistoricalMarketData,
        parameter_sets: list[tuple[int, int]],
        train_size: int,
        test_size: int,
    ) -> StrategyParameterResearchResult:

        results = []

        for fast_period, slow_period in parameter_sets:

            if fast_period <= 0:
                raise ValueError(
                    "fast_period must be positive."
                )

            if slow_period <= 0:
                raise ValueError(
                    "slow_period must be positive."
                )

            if fast_period >= slow_period:
                raise ValueError(
                    "fast_period must be smaller than slow_period."
                )

            backtest = TrendFollowingBacktester(
                fast_period=fast_period,
                slow_period=slow_period,
                transaction_cost_percent=(
                    self.transaction_cost_percent
                ),
                slippage_percent=(
                    self.slippage_percent
                ),
            ).run(data)

            walk_forward = TrendFollowingWalkForward(
                fast_period=fast_period,
                slow_period=slow_period,
                transaction_cost_percent=(
                    self.transaction_cost_percent
                ),
                slippage_percent=(
                    self.slippage_percent
                ),
            ).evaluate(
                data,
                train_size=train_size,
                test_size=test_size,
            )

            total_windows = len(
                walk_forward.windows
            )

            results.append(
                StrategyParameterResult(
                    fast_period=fast_period,
                    slow_period=slow_period,
                    backtest_return_percent=(
                        backtest.strategy_return_percent
                    ),
                    backtest_buy_and_hold_percent=(
                        backtest.buy_and_hold_return_percent
                    ),
                    max_drawdown_percent=(
                        backtest.max_drawdown_percent
                    ),
                    trade_count=(
                        backtest.trade_count
                    ),
                    walk_forward_return_percent=(
                        walk_forward.total_strategy_return_percent
                    ),
                    walk_forward_buy_and_hold_percent=(
                        walk_forward.total_buy_and_hold_return_percent
                    ),
                    positive_windows=(
                        walk_forward.positive_windows
                    ),
                    negative_windows=(
                        walk_forward.negative_windows
                    ),
                    total_windows=total_windows,
                    outperformed_walk_forward=(
                        walk_forward.total_strategy_return_percent
                        >
                        walk_forward.total_buy_and_hold_return_percent
                    ),
                )
            )

        return StrategyParameterResearchResult(
            results=tuple(results)
        )
