"""
ATLAS Strategy Memory Research Service.

Analyzes all persisted strategy-memory history.

Research-only.
This service does not generate trading decisions.
"""

from collections import defaultdict

from atlas.database.strategy_memory_repository import (
    StrategyMemoryRepository,
)
from atlas.trading.strategy_memory_history_analyzer import (
    StrategyMemoryHistoryAnalysis,
    StrategyMemoryHistoryAnalyzer,
)


class StrategyMemoryResearchResult:
    """
    Combined research result for one
    symbol/regime/strategy combination.
    """

    def __init__(
        self,
        *,
        symbol: str,
        regime: str,
        strategy_name: str,
        analysis: StrategyMemoryHistoryAnalysis,
    ):
        self.symbol = symbol
        self.regime = regime
        self.strategy_name = strategy_name
        self.analysis = analysis

    @property
    def observation_count(self):
        return self.analysis.observation_count

    @property
    def classification(self):
        return self.analysis.classification

    @property
    def consistency_score(self):
        return self.analysis.consistency_score


class StrategyMemoryResearchService:
    """
    Analyze all stored strategy-memory history.

    History is grouped by:

        symbol
        regime
        strategy_name

    Each group is independently analyzed by
    StrategyMemoryHistoryAnalyzer.
    """

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

    def analyze_all(
        self,
    ) -> tuple[StrategyMemoryResearchResult, ...]:

        records = self.repository.get_all()

        if not records:
            return ()

        groups = defaultdict(list)

        for record in records:
            groups[
                (
                    record.symbol,
                    record.regime,
                    record.strategy_name,
                )
            ].append(record)

        results = []

        for (
            symbol,
            regime,
            strategy_name,
        ), history in sorted(groups.items()):

            analysis = self.analyzer.analyze(
                tuple(
                    sorted(
                        history,
                        key=lambda record: (
                            record.updated_at
                        ),
                    )
                )
            )

            results.append(
                StrategyMemoryResearchResult(
                    symbol=symbol,
                    regime=regime,
                    strategy_name=strategy_name,
                    analysis=analysis,
                )
            )

        return tuple(results)
