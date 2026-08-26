from dataclasses import dataclass

from atlas.trading.multi_market_strategy_comparison import (
    MultiMarketStrategyComparison,
    format_multi_market_strategy_comparison,
)


@dataclass(frozen=True)
class FakeBacktest:

    max_drawdown_percent: float
    trade_count: int


@dataclass(frozen=True)
class FakeWindow:

    strategy_return_percent: float
    buy_and_hold_return_percent: float


@dataclass(frozen=True)
class FakeWalkForward:

    total_strategy_return_percent: float
    total_buy_and_hold_return_percent: float
    positive_windows: int
    negative_windows: int
    windows: tuple[FakeWindow, ...]


@dataclass(frozen=True)
class FakeResearch:

    backtest: FakeBacktest
    walk_forward: FakeWalkForward


def _research(
    strategy_return,
    benchmark_return,
    drawdown,
    trades,
    positive,
    negative,
):

    total_windows = (
        positive + negative
    )

    windows = tuple(
        FakeWindow(
            strategy_return_percent=(
                strategy_return
                / max(total_windows, 1)
            ),
            buy_and_hold_return_percent=(
                benchmark_return
                / max(total_windows, 1)
            ),
        )
        for _ in range(total_windows)
    )

    return FakeResearch(
        backtest=FakeBacktest(
            max_drawdown_percent=drawdown,
            trade_count=trades,
        ),
        walk_forward=FakeWalkForward(
            total_strategy_return_percent=(
                strategy_return
            ),
            total_buy_and_hold_return_percent=(
                benchmark_return
            ),
            positive_windows=positive,
            negative_windows=negative,
            windows=windows,
        ),
    )


def test_multi_market_comparison_runs():

    summary = (
        MultiMarketStrategyComparison()
        .compare(
            {
                "Trend Following": {
                    "BTC-USD": _research(
                        6.75,
                        23.27,
                        -4.44,
                        7,
                        2,
                        2,
                    ),
                    "ETH-USD": _research(
                        5.73,
                        29.83,
                        -4.00,
                        6,
                        3,
                        3,
                    ),
                },
            }
        )
    )

    assert summary.markets_tested == 2
    assert summary.strategies_tested == 1
    assert len(summary.results) == 2


def test_best_market_is_selected():

    summary = (
        MultiMarketStrategyComparison()
        .compare(
            {
                "Trend Following": {
                    "BTC-USD": _research(
                        6.75,
                        23.27,
                        -4.44,
                        7,
                        2,
                        2,
                    ),
                    "ETH-USD": _research(
                        12.0,
                        20.0,
                        -5.00,
                        6,
                        4,
                        2,
                    ),
                },
            }
        )
    )

    assert summary.best_market == "ETH-USD"


def test_multiple_strategies_are_scored():

    summary = (
        MultiMarketStrategyComparison()
        .compare(
            {
                "Trend Following": {
                    "BTC-USD": _research(
                        6.75,
                        23.27,
                        -4.44,
                        7,
                        2,
                        2,
                    ),
                },
                "Momentum": {
                    "BTC-USD": _research(
                        2.0,
                        23.27,
                        -3.20,
                        4,
                        1,
                        3,
                    ),
                },
            }
        )
    )

    assert len(
        summary.strategy_scores
    ) == 2


def test_empty_comparison():

    summary = (
        MultiMarketStrategyComparison()
        .compare({})
    )

    assert summary.results == ()
    assert summary.markets_tested == 0
    assert summary.strategies_tested == 0
    assert summary.best_strategy is None
    assert summary.best_market is None


def test_format_contains_market_and_strategy():

    summary = (
        MultiMarketStrategyComparison()
        .compare(
            {
                "Trend Following": {
                    "BTC-USD": _research(
                        6.75,
                        23.27,
                        -4.44,
                        7,
                        2,
                        2,
                    ),
                },
            }
        )
    )

    output = (
        format_multi_market_strategy_comparison(
            summary
        )
    )

    assert "BTC-USD" in output
    assert "Trend Following" in output
    assert "SUMMARY" in output


def test_comparison_is_deterministic():

    data = {
        "Trend Following": {
            "BTC-USD": _research(
                6.75,
                23.27,
                -4.44,
                7,
                2,
                2,
            ),
        },
        "Momentum": {
            "BTC-USD": _research(
                0.0,
                0.0,
                -3.20,
                4,
                0,
                6,
            ),
        },
    }

    comparison = (
        MultiMarketStrategyComparison()
    )

    first = comparison.compare(data)
    second = comparison.compare(data)

    assert first == second


def test_no_strategy_is_best_without_positive_edge():

    summary = (
        MultiMarketStrategyComparison()
        .compare(
            {
                "Trend Following": {
                    "BTC-USD": _research(
                        6.75,
                        23.27,
                        -4.44,
                        7,
                        2,
                        2,
                    ),
                    "ETH-USD": _research(
                        1.92,
                        29.83,
                        -6.64,
                        6,
                        2,
                        4,
                    ),
                },
                "Mean Reversion": {
                    "BTC-USD": _research(
                        0.0,
                        0.0,
                        -0.87,
                        1,
                        0,
                        6,
                    ),
                    "ETH-USD": _research(
                        0.0,
                        0.0,
                        -1.77,
                        1,
                        0,
                        6,
                    ),
                },
                "Momentum": {
                    "BTC-USD": _research(
                        0.0,
                        0.0,
                        -3.20,
                        4,
                        0,
                        6,
                    ),
                    "ETH-USD": _research(
                        0.0,
                        0.0,
                        -9.52,
                        4,
                        0,
                        6,
                    ),
                },
            }
        )
    )

    assert summary.best_strategy is None


def test_strategy_requires_positive_advantage():

    summary = (
        MultiMarketStrategyComparison()
        .compare(
            {
                "Trend Following": {
                    "BTC-USD": _research(
                        10.0,
                        20.0,
                        -4.0,
                        5,
                        4,
                        2,
                    ),
                },
            }
        )
    )

    assert summary.best_strategy is None


def test_positive_edge_can_make_strategy_eligible():

    summary = (
        MultiMarketStrategyComparison()
        .compare(
            {
                "Trend Following": {
                    "BTC-USD": _research(
                        25.0,
                        20.0,
                        -4.0,
                        5,
                        4,
                        2,
                    ),
                },
            }
        )
    )

    assert (
        summary.best_strategy
        == "Trend Following"
    )
