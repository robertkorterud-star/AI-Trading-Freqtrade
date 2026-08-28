"""
ATLAS Strategy Memory Regime Decision Adapter.

Adapts a regime strategy recommendation into a decision-compatible
representation.

Research-only.
This module does not execute trades.
"""

from dataclasses import dataclass

from atlas.models.action import Action
from atlas.trading.strategy_memory_regime_recommendation_service import (
    StrategyMemoryRegimeRecommendation,
)


@dataclass(frozen=True, slots=True)
class StrategyMemoryRegimeDecision:
    symbol: str
    regime: str
    strategy: str | None
    action: Action
    confidence: float
    independent_run_count: int
    robust_winner: bool


class StrategyMemoryRegimeDecisionAdapter:
    """
    Convert a strategy-memory recommendation into a decision representation.

    Strategy recommendations themselves are directional only when a
    concrete strategy has been recommended. Until a later decision layer
    combines this with market evidence, the safe action is HOLD.
    """

    def adapt(
        self,
        recommendation: StrategyMemoryRegimeRecommendation,
    ) -> StrategyMemoryRegimeDecision:
        if recommendation.recommended_strategy:
            action = Action.HOLD
        else:
            action = Action.HOLD

        return StrategyMemoryRegimeDecision(
            symbol=recommendation.symbol,
            regime=recommendation.regime,
            strategy=recommendation.recommended_strategy,
            action=action,
            confidence=recommendation.confidence,
            independent_run_count=recommendation.independent_run_count,
            robust_winner=recommendation.robust_winner,
        )
