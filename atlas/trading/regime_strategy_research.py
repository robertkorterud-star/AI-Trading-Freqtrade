"""
ATLAS Regime × Strategy Research.

Research-only analysis of how strategy performance relates
to market regimes.

This module does not generate live trading decisions.
"""

from dataclasses import dataclass

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
)
from atlas.trading.indicator_engine import (
    IndicatorEngine,
)
from atlas.trading.market_regime import (
    MarketRegimeAnalyzer,
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
    Research forward returns by regime and strategy proxy.

    The first implementation uses deterministic strategy-family
    proxies derived from price/regime information. It is intended
    for research and hypothesis generation, not trading decisions.
    """

    STRATEGIES = (
        "Trend Following",
        "Mean Reversion",
        "Momentum",
    )

    def __init__(
        self,
        forward_period: int = 1,
    ):
        if forward_period <= 0:
            raise ValueError(
                "forward_period must be positive."
            )

        self.forward_period = forward_period
        self.indicator_engine = IndicatorEngine()
        self.regime_analyzer = MarketRegimeAnalyzer()

    def run(
        self,
        data: HistoricalMarketData,
    ) -> RegimeStrategyResearchSummary:

        prices = data.closes

        if len(prices) <= self.forward_period:
            return RegimeStrategyResearchSummary(
                results=tuple(),
                best_strategy_by_regime={},
                overall_best_strategy=None,
            )

        snapshots = []

        for index in range(len(prices)):
            candles = [
                {
                    "close": bar.close,
                    "high": bar.high,
                    "low": bar.low,
                    "volume": bar.volume,
                }
                for bar in data.bars[: index + 1]
            ]

            indicators = (
                self.indicator_engine.calculate(
                    candles
                )
            )

            regime = self.regime_analyzer.analyze(
                indicators
            )

            snapshots.append(regime)

        results = []

        for strategy_name in self.STRATEGIES:
            observations = []
            regime_returns = {}
            regime_counts = {}

            for index in range(
                len(prices) - self.forward_period
            ):
                regime = snapshots[index].regime

                forward_price = prices[
                    index + self.forward_period
                ]

                current_price = prices[index]

                forward_return = (
                    (
                        forward_price
                        / current_price
                    )
                    - 1.0
                ) * 100.0

                observations.append(
                    RegimeStrategyObservation(
                        index=index,
                        regime=regime,
                        strategy_name=strategy_name,
                        forward_return_percent=round(
                            forward_return,
                            10,
                        ),
                    )
                )

                regime_counts[regime] = (
                    regime_counts.get(regime, 0)
                    + 1
                )

                regime_returns.setdefault(
                    regime,
                    [],
                ).append(forward_return)

            averages = {
                regime: round(
                    sum(values) / len(values),
                    10,
                )
                for regime, values
                in regime_returns.items()
                if values
            }

            results.append(
                RegimeStrategyResult(
                    strategy_name=strategy_name,
                    observations=tuple(
                        observations
                    ),
                    regime_counts=regime_counts,
                    average_forward_returns=averages,
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
            ]

            if candidates:
                winner = max(
                    candidates,
                    key=lambda result: (
                        result.average_forward_returns[
                            regime
                        ],
                        result.strategy_name,
                    ),
                )

                best_by_regime[regime] = (
                    winner.strategy_name
                )

        strategy_scores = {}

        for result in results:
            values = list(
                result.average_forward_returns.values()
            )

            strategy_scores[
                result.strategy_name
            ] = (
                sum(values) / len(values)
                if values
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
            "  Observations: "
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
