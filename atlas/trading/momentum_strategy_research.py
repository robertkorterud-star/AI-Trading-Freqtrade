"""
ATLAS Momentum Strategy Research.

Research-only assessment of momentum performance
using backtest and walk-forward evaluation.
"""

from dataclasses import dataclass

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
)
from atlas.trading.momentum_backtest import (
    MomentumBacktester,
)
from atlas.trading.momentum_walk_forward import (
    MomentumWalkForward,
)


@dataclass(frozen=True, slots=True)
class MomentumStrategyResearchResult:
    symbol: str
    points: int

    backtest: object
    walk_forward: object

    strategy_return_percent: float
    buy_and_hold_return_percent: float
    advantage_percent: float

    outperformed_buy_and_hold: bool
    verdict: str


class MomentumStrategyResearch:
    """Run the complete momentum research pipeline."""

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

    def run(
        self,
        data: HistoricalMarketData,
        *,
        train_size: int,
        test_size: int,
    ) -> MomentumStrategyResearchResult:

        backtest = MomentumBacktester(
            lookback_period=self.lookback_period,
            transaction_cost_percent=(
                self.transaction_cost_percent
            ),
            slippage_percent=(
                self.slippage_percent
            ),
        ).run(data)

        walk_forward = MomentumWalkForward(
            lookback_period=self.lookback_period,
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

        verdict = self._verdict(
            walk_forward=walk_forward,
            advantage=advantage,
        )

        return MomentumStrategyResearchResult(
            symbol=data.symbol,
            points=len(data),
            backtest=backtest,
            walk_forward=walk_forward,
            strategy_return_percent=(
                strategy_return
            ),
            buy_and_hold_return_percent=(
                benchmark_return
            ),
            advantage_percent=advantage,
            outperformed_buy_and_hold=(
                advantage > 0.0
            ),
            verdict=verdict,
        )

    @staticmethod
    def _verdict(
        *,
        walk_forward,
        advantage: float,
    ) -> str:

        if not walk_forward.windows:
            return "INCONCLUSIVE"

        if (
            walk_forward.total_strategy_return_percent
            <= 0.0
        ):
            return "NO_EDGE"

        if advantage <= 0.0:
            return "NO_EDGE"

        if (
            walk_forward.positive_windows
            <= walk_forward.negative_windows
        ):
            return "INCONCLUSIVE"

        return "EDGE"
