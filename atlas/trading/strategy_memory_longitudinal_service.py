"""
ATLAS Strategy Memory Longitudinal Service.

Loads persisted strategy-memory history and analyzes
performance across multiple research observations.

Research-only. No trading decisions.
"""

from atlas.database.strategy_memory_repository import (
    StrategyMemoryRepository,
)
from atlas.trading.strategy_memory_longitudinal_analyzer import (
    StrategyMemoryLongitudinalAnalysis,
    StrategyMemoryLongitudinalAnalyzer,
)


class StrategyMemoryLongitudinalService:
    """
    Analyze strategy performance across persisted history.

    The service is deliberately read-only with respect to
    strategy memory. It does not modify research records.
    """

    def __init__(
        self,
        repository: StrategyMemoryRepository,
        analyzer: StrategyMemoryLongitudinalAnalyzer | None = None,
    ):
        self.repository = repository
        self.analyzer = (
            analyzer
            or StrategyMemoryLongitudinalAnalyzer()
        )

    def analyze(
        self,
        *,
        symbol: str,
        regime: str,
        strategy_name: str,
    ) -> StrategyMemoryLongitudinalAnalysis:
        """Analyze all history for one strategy/regime."""

        if not symbol:
            raise ValueError(
                "symbol must not be empty."
            )

        if not regime:
            raise ValueError(
                "regime must not be empty."
            )

        if not strategy_name:
            raise ValueError(
                "strategy_name must not be empty."
            )

        history = self.repository.history(
            symbol=symbol,
            regime=regime,
            strategy_name=strategy_name,
        )

        return self.analyzer.analyze(history)

    def analyze_all(
        self,
    ) -> tuple[StrategyMemoryLongitudinalAnalysis, ...]:
        """
        Analyze every strategy/regime group in history.

        Results are returned in deterministic
        symbol/regime/strategy order.
        """

        groups = self.repository.history_groups()

        results = []

        for (
            symbol,
            regime,
            strategy_name,
        ) in groups:
            results.append(
                self.analyze(
                    symbol=symbol,
                    regime=regime,
                    strategy_name=strategy_name,
                )
            )

        return tuple(results)
