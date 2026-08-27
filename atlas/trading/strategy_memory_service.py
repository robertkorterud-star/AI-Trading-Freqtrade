"""
ATLAS Strategy Memory Service.

Transforms regime/strategy backtest research into
StrategyMemory records and optionally persists them.

Research-only. No trading decisions.
"""

from atlas.database.strategy_memory_repository import (
    StrategyMemoryRepository,
)
from atlas.trading.regime_strategy_backtest import (
    RegimeStrategyBacktestSummary,
)
from atlas.trading.strategy_memory import (
    StrategyMemory,
)
from atlas.trading.strategy_regime_recommendation import (
    StrategyRegimeRecommender,
)


class StrategyMemoryService:
    """
    Store complete regime/strategy research results.

    Every strategy result is stored in the in-memory
    StrategyMemory.

    When a repository is supplied, the same records are
    persisted to the ATLAS database.
    """

    def __init__(
        self,
        memory: StrategyMemory,
        recommender: StrategyRegimeRecommender | None = None,
        repository: StrategyMemoryRepository | None = None,
    ):
        self.memory = memory
        self.recommender = (
            recommender
            or StrategyRegimeRecommender()
        )
        self.repository = repository

    def remember(
        self,
        *,
        symbol: str,
        summary: RegimeStrategyBacktestSummary,
    ) -> None:

        if not symbol:
            raise ValueError(
                "symbol must not be empty."
            )

        regimes = {
            result.regime
            for result in summary.results
        }

        recommendations = {
            regime: self.recommender.recommend(
                summary,
                regime,
            )
            for regime in regimes
        }

        for result in summary.results:

            recommendation = recommendations[
                result.regime
            ]

            robust_winner = (
                recommendation.robust_winner
                and recommendation.recommended_strategy
                == result.strategy_name
            )

            evidence_strength = (
                recommendation.evidence_strength
                if robust_winner
                else self._evidence_strength(
                    result.trade_count
                )
            )

            record = self.memory.record(
                symbol=symbol,
                regime=result.regime,
                strategy_name=result.strategy_name,
                trade_count=result.trade_count,
                winning_trades=result.winning_trades,
                losing_trades=result.losing_trades,
                average_trade_return_percent=(
                    result.average_trade_return_percent
                ),
                total_return_percent=(
                    result.total_return_percent
                ),
                evidence_strength=evidence_strength,
                robust_winner=robust_winner,
            )

            if self.repository is not None:
                self.repository.save(record)

    @staticmethod
    def _evidence_strength(
        trade_count: int,
    ) -> str:

        if trade_count < 3:
            return "VERY_WEAK"

        if trade_count < 10:
            return "WEAK"

        if trade_count < 20:
            return "MODERATE"

        return "STRONG"
