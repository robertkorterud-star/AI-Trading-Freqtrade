"""
ATLAS Strategy Memory Regime Evidence.

Evaluates historical strategy evidence within a market regime.

Research-only.
This module does not generate trading decisions.
"""

from dataclasses import dataclass

from atlas.trading.strategy_memory_history_record import (
    StrategyMemoryHistoryRecord,
)


@dataclass(frozen=True, slots=True)
class StrategyMemoryRegimeEvidenceResult:
    symbol: str
    regime: str
    recommended_strategy: str | None
    confidence: float
    independent_run_count: int
    robust_winner: bool


class StrategyMemoryRegimeEvidence:
    """
    Evaluate whether historical strategy performance provides
    robust evidence for a regime.

    A strategy must win across all independent research runs
    considered for the regime before it can be classified as
    a robust winner.
    """

    MIN_INDEPENDENT_RUNS = 2

    # Minimum performance advantage required to establish
    # a robust winner over the next-best strategy.
    MIN_WIN_MARGIN_PERCENT = 1.0

    def evaluate(
        self,
        records: tuple[StrategyMemoryHistoryRecord, ...],
        *,
        symbol: str,
        regime: str,
    ) -> StrategyMemoryRegimeEvidenceResult:

        if not records:
            return StrategyMemoryRegimeEvidenceResult(
                symbol=symbol,
                regime=regime,
                recommended_strategy=None,
                confidence=0.0,
                independent_run_count=0,
                robust_winner=False,
            )

        run_ids = {
            record.research_run_id
            for record in records
            if record.research_run_id
        }

        independent_run_count = len(run_ids)

        if independent_run_count < self.MIN_INDEPENDENT_RUNS:
            return StrategyMemoryRegimeEvidenceResult(
                symbol=symbol,
                regime=regime,
                recommended_strategy=None,
                confidence=0.0,
                independent_run_count=independent_run_count,
                robust_winner=False,
            )

        strategies = sorted(
            {
                record.strategy_name
                for record in records
            }
        )

        winners_by_run: dict[str, set[str]] = {}

        for run_id in run_ids:
            run_records = [
                record
                for record in records
                if record.research_run_id == run_id
            ]

            if not run_records:
                continue

            best_return = max(
                record.total_return_percent
                for record in run_records
            )

            winners_by_run[run_id] = {
                record.strategy_name
                for record in run_records
                if record.total_return_percent
                == best_return
            }

        robust_candidates = [
            strategy
            for strategy in strategies
            if all(
                strategy in winners
                for winners in winners_by_run.values()
            )
        ]

        if len(robust_candidates) != 1:
            return StrategyMemoryRegimeEvidenceResult(
                symbol=symbol,
                regime=regime,
                recommended_strategy=None,
                confidence=0.0,
                independent_run_count=independent_run_count,
                robust_winner=False,
            )

        strategy = robust_candidates[0]

        # A strategy that wins every run but only by a
        # negligible margin is not considered robust.
        strategy_returns = [
            record.total_return_percent
            for record in records
            if record.strategy_name == strategy
        ]

        other_returns = [
            record.total_return_percent
            for record in records
            if record.strategy_name != strategy
        ]

        if other_returns:
            winner_average = (
                sum(strategy_returns)
                / len(strategy_returns)
            )

            runner_up_average = max(
                sum(
                    record.total_return_percent
                    for record in records
                    if record.strategy_name == other_strategy
                )
                / sum(
                    1
                    for record in records
                    if record.strategy_name == other_strategy
                )
                for other_strategy in strategies
                if other_strategy != strategy
            )

            margin = (
                winner_average
                - runner_up_average
            )

            if margin < self.MIN_WIN_MARGIN_PERCENT:
                return StrategyMemoryRegimeEvidenceResult(
                    symbol=symbol,
                    regime=regime,
                    recommended_strategy=None,
                    confidence=0.0,
                    independent_run_count=independent_run_count,
                    robust_winner=False,
                )

        confidence = round(
            min(
                100.0,
                independent_run_count / 10.0 * 100.0,
            ),
            2,
        )

        return StrategyMemoryRegimeEvidenceResult(
            symbol=symbol,
            regime=regime,
            recommended_strategy=strategy,
            confidence=confidence,
            independent_run_count=independent_run_count,
            robust_winner=True,
        )
