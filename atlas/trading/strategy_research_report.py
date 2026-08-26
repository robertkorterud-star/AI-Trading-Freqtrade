"""
ATLAS Strategy Research Report.

Converts backtest and walk-forward results into a
research-only strategy assessment.

This module does not create live trading decisions.
"""

from dataclasses import dataclass

from atlas.trading.trend_following_backtest import (
    TrendFollowingBacktestResult,
)
from atlas.trading.walk_forward import (
    WalkForwardResult,
)


@dataclass(frozen=True, slots=True)
class StrategyResearchReport:
    strategy_name: str

    strategy_return_percent: float
    buy_and_hold_return_percent: float

    max_drawdown_percent: float
    trade_count: int
    win_rate_percent: float

    walk_forward_return_percent: float
    walk_forward_buy_and_hold_return_percent: float

    positive_windows: int
    negative_windows: int
    total_windows: int

    outperformed_buy_and_hold: bool
    verdict: str


class StrategyResearchReporter:
    """Builds a conservative research report."""

    def __init__(
        self,
        strategy_name: str = "Trend Following",
    ):
        self.strategy_name = strategy_name

    def build(
        self,
        backtest: TrendFollowingBacktestResult,
        walk_forward: WalkForwardResult,
    ) -> StrategyResearchReport:

        total_windows = len(
            walk_forward.windows
        )

        outperformed = (
            backtest.strategy_return_percent
            > backtest.buy_and_hold_return_percent
            and
            walk_forward.total_strategy_return_percent
            >
            walk_forward.total_buy_and_hold_return_percent
        )

        verdict = self._verdict(
            backtest=backtest,
            walk_forward=walk_forward,
            outperformed=outperformed,
        )

        return StrategyResearchReport(
            strategy_name=self.strategy_name,
            strategy_return_percent=(
                backtest.strategy_return_percent
            ),
            buy_and_hold_return_percent=(
                backtest.buy_and_hold_return_percent
            ),
            max_drawdown_percent=(
                backtest.max_drawdown_percent
            ),
            trade_count=(
                backtest.trade_count
            ),
            win_rate_percent=(
                backtest.win_rate_percent
            ),
            walk_forward_return_percent=(
                walk_forward.total_strategy_return_percent
            ),
            walk_forward_buy_and_hold_return_percent=(
                walk_forward.total_buy_and_hold_return_percent
            ),
            positive_windows=(
                walk_forward.positive_windows
            ),
            negative_windows=(
                walk_forward.negative_windows
            ),
            total_windows=total_windows,
            outperformed_buy_and_hold=outperformed,
            verdict=verdict,
        )

    @staticmethod
    def _verdict(
        *,
        backtest: TrendFollowingBacktestResult,
        walk_forward: WalkForwardResult,
        outperformed: bool,
    ) -> str:

        # No walk-forward windows means that there is
        # insufficient evidence.
        if not walk_forward.windows:
            return "INCONCLUSIVE"

        # A strategy should not be considered to have
        # demonstrated an edge if it loses money overall.
        if (
            backtest.strategy_return_percent
            <= 0.0
            or
            walk_forward.total_strategy_return_percent
            <= 0.0
        ):
            return "NO_EDGE"

        # Require the strategy to outperform the benchmark
        # both in the complete backtest and in walk-forward.
        if not outperformed:
            return "NO_EDGE"

        # Require more positive than negative unseen windows.
        if (
            walk_forward.positive_windows
            <= walk_forward.negative_windows
        ):
            return "INCONCLUSIVE"

        return "EDGE"


def format_research_report(
    report: StrategyResearchReport,
) -> str:
    """Render a compact human-readable research report."""

    lines = [
        "ATLAS Strategy Research",
        "=======================",
        "",
        f"Strategy: {report.strategy_name}",
        "",
        "Backtest",
        "--------",
        (
            "Strategy return: "
            f"{report.strategy_return_percent:.2f}%"
        ),
        (
            "Buy & Hold return: "
            f"{report.buy_and_hold_return_percent:.2f}%"
        ),
        (
            "Max drawdown: "
            f"{report.max_drawdown_percent:.2f}%"
        ),
        (
            f"Trades: {report.trade_count}"
        ),
        (
            "Win rate: "
            f"{report.win_rate_percent:.2f}%"
        ),
        "",
        "Walk-forward",
        "------------",
        (
            "Strategy return: "
            f"{report.walk_forward_return_percent:.2f}%"
        ),
        (
            "Buy & Hold return: "
            f"{report.walk_forward_buy_and_hold_return_percent:.2f}%"
        ),
        (
            "Positive windows: "
            f"{report.positive_windows}"
        ),
        (
            "Negative windows: "
            f"{report.negative_windows}"
        ),
        (
            "Total windows: "
            f"{report.total_windows}"
        ),
        "",
        (
            "Outperformed Buy & Hold: "
            f"{report.outperformed_buy_and_hold}"
        ),
        "",
        f"VERDICT: {report.verdict}",
    ]

    return "\n".join(lines)
