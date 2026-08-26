from dataclasses import dataclass

from atlas.trading.strategy_comparison import (
    StrategyComparison,
    format_strategy_comparison,
)


@dataclass(frozen=True)
class FakeBacktest:

    max_drawdown_percent: float
    trade_count: int
    win_rate_percent: float


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
    win_rate,
    positive,
    negative,
):

    windows = tuple(
        FakeWindow(
            strategy_return_percent=(
                strategy_return
                / max(
                    positive + negative,
                    1,
                )
            ),
            buy_and_hold_return_percent=(
                benchmark_return
                / max(
                    positive + negative,
                    1,
                )
            ),
        )
        for _ in range(
            positive + negative
        )
    )

    return FakeResearch(
        backtest=FakeBacktest(
            max_drawdown_percent=drawdown,
            trade_count=trades,
            win_rate_percent=win_rate,
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


def test_comparison_runs():

    summary = StrategyComparison().compare(
        {
            "Trend Following": _research(
                6.75,
                23.27,
                -4.44,
                7,
                71.43,
                2,
                2,
            ),
            "Mean Reversion": _research(
                0.0,
                0.0,
                -0.87,
                1,
                100.0,
                0,
                6,
            ),
            "Momentum": _research(
                0.0,
                0.0,
                -3.20,
                4,
                50.0,
                0,
                6,
            ),
        }
    )

    assert len(summary.results) == 3
    assert summary.overall_winner == "Trend Following"


def test_best_drawdown_is_selected():

    summary = StrategyComparison().compare(
        {
            "Trend Following": _research(
                6.75,
                23.27,
                -4.44,
                7,
                71.43,
                2,
                2,
            ),
            "Mean Reversion": _research(
                0.0,
                0.0,
                -0.87,
                1,
                100.0,
                0,
                6,
            ),
        }
    )

    assert (
        summary.best_drawdown
        == "Mean Reversion"
    )


def test_best_advantage_is_selected():

    summary = StrategyComparison().compare(
        {
            "Trend Following": _research(
                6.75,
                23.27,
                -4.44,
                7,
                71.43,
                2,
                2,
            ),
            "Momentum": _research(
                10.0,
                20.0,
                -3.20,
                4,
                50.0,
                4,
                2,
            ),
        }
    )

    assert (
        summary.best_advantage
        == "Momentum"
    )


def test_robustness_is_preserved():

    summary = StrategyComparison().compare(
        {
            "Trend Following": _research(
                6.75,
                23.27,
                -4.44,
                7,
                71.43,
                2,
                2,
            ),
            "Momentum": _research(
                5.0,
                10.0,
                -3.20,
                4,
                50.0,
                4,
                2,
            ),
        },
        robustness={
            "Trend Following": False,
            "Momentum": True,
        },
    )

    assert summary.most_robust == "Momentum"


def test_empty_comparison():

    summary = StrategyComparison().compare({})

    assert summary.results == ()
    assert summary.overall_winner is None


def test_format_contains_strategy_names():

    summary = StrategyComparison().compare(
        {
            "Trend Following": _research(
                6.75,
                23.27,
                -4.44,
                7,
                71.43,
                2,
                2,
            ),
            "Momentum": _research(
                0.0,
                0.0,
                -3.20,
                4,
                50.0,
                0,
                6,
            ),
        }
    )

    output = format_strategy_comparison(
        summary
    )

    assert "Trend Following" in output
    assert "Momentum" in output
    assert "Overall winner:" in output


def test_comparison_is_deterministic():

    data = {
        "Trend Following": _research(
            6.75,
            23.27,
            -4.44,
            7,
            71.43,
            2,
            2,
        ),
        "Mean Reversion": _research(
            0.0,
            0.0,
            -0.87,
            1,
            100.0,
            0,
            6,
        ),
    }

    first = StrategyComparison().compare(
        data
    )

    second = StrategyComparison().compare(
        data
    )

    assert first == second
