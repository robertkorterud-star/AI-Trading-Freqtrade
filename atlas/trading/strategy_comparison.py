"""
ATLAS Strategy Comparison.

Compares research results from multiple strategy families.

Research-only. No live trading decisions.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StrategyComparisonResult:
    strategy_name: str

    strategy_return_percent: float
    buy_and_hold_return_percent: float
    advantage_percent: float

    max_drawdown_percent: float
    trade_count: int
    win_rate_percent: float

    positive_windows: int
    negative_windows: int
    total_windows: int

    robust: bool


@dataclass(frozen=True, slots=True)
class StrategyComparisonSummary:
    results: tuple[StrategyComparisonResult, ...]

    best_walk_forward: str | None
    best_advantage: str | None
    best_drawdown: str | None
    most_robust: str | None

    overall_winner: str | None


class StrategyComparison:
    """Compare multiple completed strategy research results."""

    def compare(
        self,
        results: dict[str, object],
        *,
        robustness: dict[str, bool] | None = None,
    ) -> StrategyComparisonSummary:

        robustness = robustness or {}

        comparison_results = []

        for strategy_name, result in results.items():

            backtest = result.backtest
            walk_forward = result.walk_forward

            strategy_return = (
                walk_forward.total_strategy_return_percent
            )

            benchmark_return = (
                walk_forward.total_buy_and_hold_return_percent
            )

            advantage = (
                strategy_return
                - benchmark_return
            )

            comparison_results.append(
                StrategyComparisonResult(
                    strategy_name=strategy_name,
                    strategy_return_percent=(
                        strategy_return
                    ),
                    buy_and_hold_return_percent=(
                        benchmark_return
                    ),
                    advantage_percent=advantage,
                    max_drawdown_percent=(
                        backtest.max_drawdown_percent
                    ),
                    trade_count=(
                        backtest.trade_count
                    ),
                    win_rate_percent=(
                        backtest.win_rate_percent
                    ),
                    positive_windows=(
                        walk_forward.positive_windows
                    ),
                    negative_windows=(
                        walk_forward.negative_windows
                    ),
                    total_windows=(
                        len(walk_forward.windows)
                    ),
                    robust=(
                        robustness.get(
                            strategy_name,
                            False,
                        )
                    ),
                )
            )

        if not comparison_results:
            return StrategyComparisonSummary(
                results=(),
                best_walk_forward=None,
                best_advantage=None,
                best_drawdown=None,
                most_robust=None,
                overall_winner=None,
            )

        best_walk_forward = max(
            comparison_results,
            key=lambda item: (
                item.strategy_return_percent,
                item.advantage_percent,
            ),
        ).strategy_name

        best_advantage = max(
            comparison_results,
            key=lambda item: (
                item.advantage_percent,
                item.strategy_return_percent,
            ),
        ).strategy_name

        best_drawdown = max(
            comparison_results,
            key=lambda item: (
                item.max_drawdown_percent,
            ),
        ).strategy_name

        robust_results = [
            item
            for item in comparison_results
            if item.robust
        ]

        most_robust = (
            max(
                robust_results,
                key=lambda item: (
                    item.advantage_percent,
                    item.strategy_return_percent,
                ),
            ).strategy_name
            if robust_results
            else None
        )

        ranked = sorted(
            comparison_results,
            key=lambda item: (
                item.strategy_return_percent,
                item.advantage_percent,
                item.max_drawdown_percent,
            ),
            reverse=True,
        )

        overall_winner = ranked[0].strategy_name

        return StrategyComparisonSummary(
            results=tuple(
                comparison_results
            ),
            best_walk_forward=(
                best_walk_forward
            ),
            best_advantage=(
                best_advantage
            ),
            best_drawdown=(
                best_drawdown
            ),
            most_robust=(
                most_robust
            ),
            overall_winner=(
                overall_winner
            ),
        )


def format_strategy_comparison(
    summary: StrategyComparisonSummary,
) -> str:
    """Render a compact comparison report."""

    lines = [
        "ATLAS STRATEGY COMPARISON",
        "=========================",
        "",
    ]

    for result in summary.results:

        lines.append(
            f"{result.strategy_name}"
        )

        lines.append(
            "  Walk-forward: "
            f"{result.strategy_return_percent:.2f}%"
        )

        lines.append(
            "  Buy & Hold:   "
            f"{result.buy_and_hold_return_percent:.2f}%"
        )

        lines.append(
            "  Advantage:     "
            f"{result.advantage_percent:.2f}%"
        )

        lines.append(
            "  Max drawdown:  "
            f"{result.max_drawdown_percent:.2f}%"
        )

        lines.append(
            "  Trades:        "
            f"{result.trade_count}"
        )

        lines.append(
            "  Win rate:      "
            f"{result.win_rate_percent:.2f}%"
        )

        lines.append(
            "  Windows:       "
            f"{result.positive_windows}/"
            f"{result.total_windows}"
        )

        lines.append(
            "  Robust:        "
            f"{result.robust}"
        )

        lines.append("")

    lines.extend(
        [
            "SUMMARY",
            "-------",
            (
                "Best walk-forward: "
                f"{summary.best_walk_forward}"
            ),
            (
                "Best advantage:    "
                f"{summary.best_advantage}"
            ),
            (
                "Best drawdown:     "
                f"{summary.best_drawdown}"
            ),
            (
                "Most robust:       "
                f"{summary.most_robust}"
            ),
            (
                "Overall winner:    "
                f"{summary.overall_winner}"
            ),
        ]
    )

    return "\n".join(lines)
