"""
ATLAS Strategy Robustness Research.

Evaluates the same strategy parameters across multiple
historical datasets.

Research-only. No live trading decisions.
"""

from dataclasses import dataclass

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
)
from atlas.trading.walk_forward import (
    TrendFollowingWalkForward,
)


@dataclass(frozen=True, slots=True)
class StrategyRobustnessResult:
    symbol: str
    timeframe: str
    source: str

    fast_period: int
    slow_period: int

    walk_forward_return_percent: float
    buy_and_hold_return_percent: float
    advantage_percent: float

    positive_windows: int
    negative_windows: int
    total_windows: int

    outperformed_buy_and_hold: bool


@dataclass(frozen=True, slots=True)
class StrategyRobustnessSummary:
    results: tuple[StrategyRobustnessResult, ...]

    datasets_tested: int
    datasets_outperformed: int
    outperformance_ratio_percent: float
    average_advantage_percent: float

    robust: bool

    @property
    def best(self) -> StrategyRobustnessResult | None:
        if not self.results:
            return None

        return max(
            self.results,
            key=lambda result: (
                result.advantage_percent,
                result.positive_windows
                - result.negative_windows,
            ),
        )


class StrategyRobustnessResearch:
    """Evaluate parameters across multiple datasets."""

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
        datasets: list[HistoricalMarketData],
        *,
        fast_period: int,
        slow_period: int,
        train_size: int,
        test_size: int,
    ) -> StrategyRobustnessSummary:

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

        results = []

        for data in datasets:

            walk_forward = (
                TrendFollowingWalkForward(
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
            )

            strategy_return = (
                walk_forward.total_strategy_return_percent
            )

            benchmark_return = (
                walk_forward.total_buy_and_hold_return_percent
            )

            advantage = (
                strategy_return
                - benchmark_return
            )

            total_windows = len(
                walk_forward.windows
            )

            results.append(
                StrategyRobustnessResult(
                    symbol=data.symbol,
                    timeframe=data.timeframe,
                    source=data.source,
                    fast_period=fast_period,
                    slow_period=slow_period,
                    walk_forward_return_percent=(
                        strategy_return
                    ),
                    buy_and_hold_return_percent=(
                        benchmark_return
                    ),
                    advantage_percent=advantage,
                    positive_windows=(
                        walk_forward.positive_windows
                    ),
                    negative_windows=(
                        walk_forward.negative_windows
                    ),
                    total_windows=total_windows,
                    outperformed_buy_and_hold=(
                        advantage > 0.0
                    ),
                )
            )

        datasets_tested = len(results)

        datasets_outperformed = sum(
            result.outperformed_buy_and_hold
            for result in results
        )

        outperformance_ratio = (
            datasets_outperformed
            / datasets_tested
            * 100.0
            if datasets_tested
            else 0.0
        )

        average_advantage = (
            sum(
                result.advantage_percent
                for result in results
            )
            / datasets_tested
            if datasets_tested
            else 0.0
        )

        robust = (
            datasets_tested > 0
            and datasets_outperformed
            > datasets_tested / 2
        )

        return StrategyRobustnessSummary(
            results=tuple(results),
            datasets_tested=datasets_tested,
            datasets_outperformed=(
                datasets_outperformed
            ),
            outperformance_ratio_percent=(
                outperformance_ratio
            ),
            average_advantage_percent=(
                average_advantage
            ),
            robust=robust,
        )
