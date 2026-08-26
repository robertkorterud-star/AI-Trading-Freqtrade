"""
ATLAS Historical Strategy Research.

Orchestrates historical market data through backtesting,
walk-forward evaluation and strategy research reporting.
"""

from dataclasses import dataclass

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
)
from atlas.trading.strategy_research_report import (
    StrategyResearchReporter,
)
from atlas.trading.trend_following_backtest import (
    TrendFollowingBacktester,
)
from atlas.trading.walk_forward import (
    TrendFollowingWalkForward,
)


@dataclass(frozen=True, slots=True)
class HistoricalStrategyResearchResult:
    symbol: str
    points: int
    backtest: object
    walk_forward: object
    report: object


class HistoricalStrategyResearch:
    """Run the complete historical research pipeline."""

    def __init__(
        self,
        fast_period: int = 5,
        slow_period: int = 15,
        transaction_cost_percent: float = 0.1,
        slippage_percent: float = 0.05,
    ):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.transaction_cost_percent = (
            transaction_cost_percent
        )
        self.slippage_percent = slippage_percent

    def run(
        self,
        data: HistoricalMarketData,
        train_size: int,
        test_size: int,
    ) -> HistoricalStrategyResearchResult:

        backtest = TrendFollowingBacktester(
            fast_period=self.fast_period,
            slow_period=self.slow_period,
            transaction_cost_percent=(
                self.transaction_cost_percent
            ),
            slippage_percent=(
                self.slippage_percent
            ),
        ).run(data)

        walk_forward = TrendFollowingWalkForward(
            fast_period=self.fast_period,
            slow_period=self.slow_period,
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

        report = StrategyResearchReporter().build(
            backtest=backtest,
            walk_forward=walk_forward,
        )

        return HistoricalStrategyResearchResult(
            symbol=data.symbol,
            points=len(data),
            backtest=backtest,
            walk_forward=walk_forward,
            report=report,
        )
