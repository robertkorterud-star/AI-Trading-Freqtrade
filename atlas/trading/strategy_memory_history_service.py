"""
ATLAS Strategy Memory History Service.

Reads persisted strategy-memory history and analyzes
performance consistency across research runs.

Research-only.
This service does not generate trading decisions.
"""

from atlas.database.strategy_memory_repository import (
    StrategyMemoryRepository,
)
from atlas.trading.strategy_memory_history_analyzer import (
    StrategyMemoryHistoryAnalysis,
    StrategyMemoryHistoryAnalyzer,
)


class StrategyMemoryHistoryService:
    """Analyze persisted strategy-memory history."""

    def __init__(
        self,
        repository: StrategyMemoryRepository,
        analyzer: StrategyMemoryHistoryAnalyzer | None = None,
    ):
        self.repository = repository
        self.analyzer = (
            analyzer
            or StrategyMemoryHistoryAnalyzer()
        )

    def analyze(
        self,
        *,
        symbol: str,
        regime: str,
        strategy_name: str,
    ) -> StrategyMemoryHistoryAnalysis:

        history = self.repository.history(
            symbol=symbol,
            regime=regime,
            strategy_name=strategy_name,
        )

        return self.analyzer.analyze(history)
