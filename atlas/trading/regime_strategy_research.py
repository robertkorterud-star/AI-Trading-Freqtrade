"""
ATLAS Regime × Strategy Research.

Research-only analysis of actual strategy performance
across market regimes.

This module uses the existing strategy backtest research
and does not generate live trading decisions.
"""

from dataclasses import dataclass

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
)
from atlas.trading.regime_strategy_backtest import (
    RegimeStrategyBacktestResearch,
)


@dataclass(frozen=True, slots=True)
class RegimeStrategyObservation:
    index: int
    regime: str
    strategy_name: str
    forward_return_percent: float


@dataclass(frozen=True, slots=True)
class RegimeStrategyResult:
    strategy_name: str
    observations: tuple[
        RegimeStrategyObservation,
        ...
    ]
    regime_counts: dict[str, int]
    average_forward_returns: dict[str, float]

    @property
    def classified_observations(self) -> int:
        return len(self.observations)

    @property
    def best_regime(self) -> str | None:
        if not self.average_forward_returns:
            return None

        return max(
            self.average_forward_returns,
            key=self.average_forward_returns.get,
        )


@dataclass(frozen=True, slots=True)
class RegimeStrategyResearchSummary:
    results: tuple[RegimeStrategyResult, ...]

    best_strategy_by_regime: dict[str, str]

    overall_best_strategy: str | None


class RegimeStrategyResearch:
    """
    Analyze actual strategy trades by entry regime.

    Unlike the earlier proxy implementation, this class
    uses the existing strategy backtest engine so that
    strategy results are based on real strategy trades.
    """

    def __init__(
        self,
        transaction_cost_percent: float = 0.1,
        slippage_percent: float = 0.05,
    ):
        if transaction_cost_percent < 0:
            raise ValueError(
                "transaction_cost_percent "
                "cannot be negative."
            )

        if slippage_percent < 0:
            raise ValueError(
                "slippage_percent "
                "cannot be negative."
            )

        self.transaction_cost_percent = (
            float(transaction_cost_percent)
        )
        self.slippage_percent = (
            float(slippage_percent)
        )

    def run(
        self,
        data: HistoricalMarketData,
    ) -> RegimeStrategyResearchSummary:

        summary = (
            RegimeStrategyBacktestResearch(
                transaction_cost_percent=(
                    self.transaction_cost_percent
                ),
                slippage_percent=(
                    self.slippage_percent
                ),
            ).run(data)
        )

        results_by_strategy = {}

        for result in summary.results:
            results_by_strategy.setdefault(
                result.strategy_name,
                [],
            ).append(result)

        results = []

        for strategy_name in sorted(
            results_by_strategy
        ):
            strategy_results = (
                results_by_strategy[strategy_name]
            )

            observations = []

            for regime_result in strategy_results:
                for index in range(
                    regime_result.trade_count
                ):
                    observations.append(
                        RegimeStrategyObservation(
                            index=index,
                            regime=regime_result.regime,
                            strategy_name=strategy_name,
                            forward_return_percent=(
                                regime_result
                                .average_trade_return_percent
                            ),
                        )
                    )

            regime_counts = {
                result.regime: result.trade_count
                for result in strategy_results
            }

            average_returns = {
                result.regime: (
                    result.average_trade_return_percent
                )
                for result in strategy_results
            }

            results.append(
                RegimeStrategyResult(
                    strategy_name=strategy_name,
                    observations=tuple(observations),
                    regime_counts=regime_counts,
                    average_forward_returns=(
                        average_returns
                    ),
                )
            )

        best_by_regime = {}

        all_regimes = set()

        for result in results:
            all_regimes.update(
                result.average_forward_returns
            )

        for regime in sorted(all_regimes):
            candidates = [
                result
                for result in results
                if regime
                in result.average_forward_returns
                and result.regime_counts.get(
                    regime,
                    0,
                ) > 0
            ]

            if candidates:
                winner = max(
                    candidates,
                    key=lambda result: (
                        result.average_forward_returns[
                            regime
                        ],
                        result.regime_counts.get(
                            regime,
                            0,
                        ),
                        result.strategy_name,
                    ),
                )

                best_by_regime[regime] = (
                    winner.strategy_name
                )

        strategy_scores = {}

        for result in results:
            weighted_returns = []
            total_trades = 0

            for regime, average_return in (
                result.average_forward_returns.items()
            ):
                count = result.regime_counts.get(
                    regime,
                    0,
                )

                if count <= 0:
                    continue

                weighted_returns.extend(
                    [average_return] * count
                )

                total_trades += count

            strategy_scores[result.strategy_name] = (
                sum(weighted_returns)
                / total_trades
                if total_trades
                else float("-inf")
            )

        overall_best = (
            max(
                strategy_scores,
                key=strategy_scores.get,
            )
            if strategy_scores
            else None
        )

        return RegimeStrategyResearchSummary(
            results=tuple(results),
            best_strategy_by_regime=best_by_regime,
            overall_best_strategy=overall_best,
        )


def format_regime_strategy_research(
    summary: RegimeStrategyResearchSummary,
) -> str:
    """Render a compact regime × strategy report."""

    lines = [
        "ATLAS REGIME × STRATEGY RESEARCH",
        "=================================",
        "",
    ]

    for result in summary.results:
        lines.append(
            result.strategy_name
        )

        lines.append(
            "  Trades: "
            f"{result.classified_observations}"
        )

        for regime in sorted(
            result.average_forward_returns
        ):
            count = result.regime_counts.get(
                regime,
                0,
            )

            average = (
                result.average_forward_returns[
                    regime
                ]
            )

            lines.append(
                f"  {regime:18} "
                f"{count:4} "
                f"{average:8.3f}%"
            )

        lines.append("")

    lines.extend(
        [
            "BEST STRATEGY BY REGIME",
            "------------------------",
        ]
    )

    for regime, strategy in (
        summary.best_strategy_by_regime.items()
    ):
        lines.append(
            f"{regime:18} {strategy}"
        )

    lines.append("")
    lines.append(
        "Overall best strategy: "
        f"{summary.overall_best_strategy}"
    )

    return "\n".join(lines)
