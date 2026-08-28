"""
ATLAS Strategy Memory Regime Recommendation Service.

Turns regime evidence into an actionable strategy recommendation.

Research-only.
This module does not execute trades.
"""

from dataclasses import dataclass

from atlas.trading.strategy_memory_regime_evidence import (
    StrategyMemoryRegimeEvidenceResult,
)


@dataclass(frozen=True, slots=True)
class StrategyMemoryRegimeRecommendation:
    symbol: str
    regime: str
    recommended_strategy: str | None
    confidence: float
    independent_run_count: int
    robust_winner: bool


class StrategyMemoryRegimeRecommendationService:
    """
    Convert regime evidence into a strategy recommendation.

    A recommendation is only produced when:
    - a strategy exists,
    - the evidence identifies a robust winner,
    - confidence meets the configured minimum threshold.
    """

    def __init__(
        self,
        minimum_confidence: float = 0.0,
    ):
        if not 0.0 <= minimum_confidence <= 100.0:
            raise ValueError(
                "minimum_confidence must be between 0 and 100"
            )

        self.minimum_confidence = minimum_confidence

    def recommend(
        self,
        result: StrategyMemoryRegimeEvidenceResult,
    ) -> StrategyMemoryRegimeRecommendation:

        strategy = result.recommended_strategy

        if not strategy:
            return self._none(result)

        if not result.robust_winner:
            return self._none(result)

        if result.confidence < self.minimum_confidence:
            return self._none(result)

        return StrategyMemoryRegimeRecommendation(
            symbol=result.symbol,
            regime=result.regime,
            recommended_strategy=strategy,
            confidence=result.confidence,
            independent_run_count=result.independent_run_count,
            robust_winner=True,
        )

    @staticmethod
    def _none(
        result: StrategyMemoryRegimeEvidenceResult,
    ) -> StrategyMemoryRegimeRecommendation:
        return StrategyMemoryRegimeRecommendation(
            symbol=result.symbol,
            regime=result.regime,
            recommended_strategy=None,
            confidence=result.confidence,
            independent_run_count=result.independent_run_count,
            robust_winner=False,
        )
