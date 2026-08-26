"""
ATLAS Multi-Market Strategy Comparison.

Compares strategy performance across multiple
historical market datasets.

Research-only. No live trading decisions.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MarketStrategyResult:
    symbol: str
    strategy_name: str

    walk_forward_return_percent: float
    buy_and_hold_return_percent: float
    advantage_percent: float

    positive_windows: int
    negative_windows: int
    total_windows: int

    max_drawdown_percent: float
    trade_count: int


@dataclass(frozen=True, slots=True)
class MultiMarketStrategySummary:
    results: tuple[MarketStrategyResult, ...]

    markets_tested: int
    strategies_tested: int

    strategy_scores: dict[str, float]

    best_strategy: str | None
    best_market: str | None


class MultiMarketStrategyComparison:
    """Compare strategies across multiple markets."""

    def compare(
        self,
        research_results: dict[
            str,
            dict[str, object],
        ],
    ) -> MultiMarketStrategySummary:

        results = []

        for strategy_name, markets in (
            research_results.items()
        ):

            for symbol, research in markets.items():

                backtest = research.backtest
                walk_forward = research.walk_forward

                strategy_return = (
                    walk_forward
                    .total_strategy_return_percent
                )

                benchmark_return = (
                    walk_forward
                    .total_buy_and_hold_return_percent
                )

                advantage = (
                    strategy_return
                    - benchmark_return
                )

                results.append(
                    MarketStrategyResult(
                        symbol=symbol,
                        strategy_name=strategy_name,
                        walk_forward_return_percent=(
                            strategy_return
                        ),
                        buy_and_hold_return_percent=(
                            benchmark_return
                        ),
                        advantage_percent=advantage,
                        positive_windows=(
                            walk_forward
                            .positive_windows
                        ),
                        negative_windows=(
                            walk_forward
                            .negative_windows
                        ),
                        total_windows=len(
                            walk_forward.windows
                        ),
                        max_drawdown_percent=(
                            backtest
                            .max_drawdown_percent
                        ),
                        trade_count=(
                            backtest.trade_count
                        ),
                    )
                )

        symbols = {
            result.symbol
            for result in results
        }

        strategies = {
            result.strategy_name
            for result in results
        }

        scores = {}

        for strategy_name in strategies:

            strategy_results = [
                result
                for result in results
                if result.strategy_name
                == strategy_name
            ]

            if not strategy_results:
                continue

            average_advantage = (
                sum(
                    result.advantage_percent
                    for result in strategy_results
                )
                / len(strategy_results)
            )

            positive_ratio = (
                sum(
                    result.positive_windows
                    for result in strategy_results
                )
                /
                max(
                    sum(
                        result.total_windows
                        for result in strategy_results
                    ),
                    1,
                )
            )

            scores[strategy_name] = (
                average_advantage
                + positive_ratio * 10.0
            )

        eligible_strategies = {}

        for strategy_name in strategies:

            strategy_results = [
                result
                for result in results
                if result.strategy_name
                == strategy_name
            ]

            if not strategy_results:
                continue

            has_positive_return = any(
                result.walk_forward_return_percent
                > 0.0
                for result in strategy_results
            )

            has_positive_advantage = any(
                result.advantage_percent
                > 0.0
                for result in strategy_results
            )

            has_positive_window = any(
                result.positive_windows
                > 0
                for result in strategy_results
            )

            if (
                has_positive_return
                and has_positive_advantage
                and has_positive_window
            ):
                eligible_strategies[
                    strategy_name
                ] = scores[strategy_name]

        best_strategy = (
            max(
                eligible_strategies,
                key=eligible_strategies.get,
            )
            if eligible_strategies
            else None
        )

        best_market = None

        if results:
            best_market = max(
                results,
                key=lambda result: (
                    result.advantage_percent,
                    result.walk_forward_return_percent,
                ),
            ).symbol

        return MultiMarketStrategySummary(
            results=tuple(results),
            markets_tested=len(symbols),
            strategies_tested=len(strategies),
            strategy_scores=scores,
            best_strategy=best_strategy,
            best_market=best_market,
        )


def format_multi_market_strategy_comparison(
    summary: MultiMarketStrategySummary,
) -> str:
    """Render a compact multi-market research report."""

    lines = [
        "ATLAS MULTI-MARKET STRATEGY COMPARISON",
        "=======================================",
        "",
    ]

    for result in summary.results:

        lines.append(
            f"{result.symbol} | "
            f"{result.strategy_name}"
        )

        lines.append(
            "  Walk-forward: "
            f"{result.walk_forward_return_percent:.2f}%"
        )

        lines.append(
            "  Buy & Hold:   "
            f"{result.buy_and_hold_return_percent:.2f}%"
        )

        lines.append(
            "  Advantage:    "
            f"{result.advantage_percent:.2f}%"
        )

        lines.append(
            "  Drawdown:     "
            f"{result.max_drawdown_percent:.2f}%"
        )

        lines.append(
            "  Windows:      "
            f"{result.positive_windows}/"
            f"{result.total_windows}"
        )

        lines.append("")

    lines.extend(
        [
            "SUMMARY",
            "-------",
            (
                "Markets tested:   "
                f"{summary.markets_tested}"
            ),
            (
                "Strategies tested:"
                f" {summary.strategies_tested}"
            ),
            (
                "Best strategy:    "
                f"{summary.best_strategy}"
            ),
            (
                "Best market:      "
                f"{summary.best_market}"
            ),
            "",
            "Strategy scores:",
        ]
    )

    for (
        strategy_name,
        score,
    ) in sorted(
        summary.strategy_scores.items()
    ):

        lines.append(
            f"  {strategy_name}: "
            f"{score:.2f}"
        )

    return "\n".join(lines)
