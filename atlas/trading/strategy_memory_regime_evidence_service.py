"""
ATLAS Strategy Memory Regime Evidence Service.

Coordinates repository history with regime evidence analysis.

Research-only.
This service does not generate trading decisions.
"""

from atlas.database.strategy_memory_repository import (
    StrategyMemoryRepository,
)
from atlas.trading.strategy_memory_regime_evidence import (
    StrategyMemoryRegimeEvidence,
    StrategyMemoryRegimeEvidenceResult,
)


class StrategyMemoryRegimeEvidenceService:
    """
    Analyze historical strategy evidence for market regimes.
    """

    def __init__(
        self,
        repository: StrategyMemoryRepository,
        analyzer: StrategyMemoryRegimeEvidence | None = None,
    ):
        self.repository = repository
        self.analyzer = (
            analyzer
            if analyzer is not None
            else StrategyMemoryRegimeEvidence()
        )

    def analyze(
        self,
        *,
        symbol: str,
        regime: str,
    ) -> StrategyMemoryRegimeEvidenceResult:

        history = self._history_for_regime(
            symbol=symbol,
            regime=regime,
        )

        return self.analyzer.evaluate(
            history,
            symbol=symbol,
            regime=regime,
        )

    def analyze_all(
        self,
    ) -> tuple[StrategyMemoryRegimeEvidenceResult, ...]:

        groups = sorted(
            {
                (symbol, regime)
                for symbol, regime, _strategy_name
                in self.repository.history_groups()
            }
        )

        return tuple(
            self.analyze(
                symbol=symbol,
                regime=regime,
            )
            for symbol, regime in groups
        )

    def _history_for_regime(
        self,
        *,
        symbol: str,
        regime: str,
    ):
        records = []

        for (
            group_symbol,
            group_regime,
            strategy_name,
        ) in self.repository.history_groups():

            if (
                group_symbol != symbol
                or group_regime != regime
            ):
                continue

            records.extend(
                self.repository.history(
                    symbol=group_symbol,
                    regime=group_regime,
                    strategy_name=strategy_name,
                )
            )

        return tuple(
            sorted(
                records,
                key=lambda record: (
                    record.research_run_id,
                    record.strategy_name,
                    record.recorded_at,
                ),
            )
        )
