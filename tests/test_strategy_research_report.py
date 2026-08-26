from dataclasses import replace

from atlas.trading.strategy_research_report import (
    StrategyResearchReporter,
    format_research_report,
)
from atlas.trading.trend_following_backtest import (
    TrendFollowingBacktestResult,
)
from atlas.trading.walk_forward import (
    TrendFollowingWalkForward,
)


def _backtest(
    strategy_return=30.0,
    buy_and_hold_return=20.0,
):
    return TrendFollowingBacktestResult(
        initial_capital=10000.0,
        final_capital=13000.0,
        strategy_return_percent=strategy_return,
        buy_and_hold_return_percent=buy_and_hold_return,
        max_drawdown_percent=-10.0,
        trade_count=10,
        winning_trades=6,
        losing_trades=4,
        win_rate_percent=60.0,
        transaction_cost_percent=0.1,
        slippage_percent=0.05,
        trades=(),
    )


def _walk_forward(
    strategy_return=30.0,
    buy_and_hold_return=20.0,
    positive=3,
    negative=1,
):
    return TrendFollowingWalkForward(
        fast_period=3,
        slow_period=8,
    ).evaluate(
        list(range(100, 300)),
        train_size=50,
        test_size=25,
    )


def _manual_walk_forward(
    strategy_return,
    buy_and_hold_return,
    positive,
    negative,
):
    base = _walk_forward()

    windows = list(base.windows)

    return replace(
        base,
        windows=tuple(windows[:positive + negative]),
        total_strategy_return_percent=(
            strategy_return
        ),
        total_buy_and_hold_return_percent=(
            buy_and_hold_return
        ),
        positive_windows=positive,
        negative_windows=negative,
    )


def test_report_detects_edge():

    backtest = _backtest(
        strategy_return=30.0,
        buy_and_hold_return=20.0,
    )

    walk_forward = _manual_walk_forward(
        strategy_return=25.0,
        buy_and_hold_return=15.0,
        positive=3,
        negative=1,
    )

    report = StrategyResearchReporter().build(
        backtest,
        walk_forward,
    )

    assert report.verdict == "EDGE"
    assert report.outperformed_buy_and_hold is True


def test_report_rejects_strategy_that_loses():

    backtest = _backtest(
        strategy_return=-5.0,
        buy_and_hold_return=20.0,
    )

    walk_forward = _manual_walk_forward(
        strategy_return=-4.0,
        buy_and_hold_return=15.0,
        positive=1,
        negative=3,
    )

    report = StrategyResearchReporter().build(
        backtest,
        walk_forward,
    )

    assert report.verdict == "NO_EDGE"


def test_report_rejects_strategy_that_loses_to_benchmark():

    backtest = _backtest(
        strategy_return=10.0,
        buy_and_hold_return=30.0,
    )

    walk_forward = _manual_walk_forward(
        strategy_return=8.0,
        buy_and_hold_return=25.0,
        positive=3,
        negative=1,
    )

    report = StrategyResearchReporter().build(
        backtest,
        walk_forward,
    )

    assert report.verdict == "NO_EDGE"


def test_report_is_inconclusive_without_windows():

    backtest = _backtest()

    walk_forward = _manual_walk_forward(
        strategy_return=0.0,
        buy_and_hold_return=0.0,
        positive=0,
        negative=0,
    )

    walk_forward = replace(
        walk_forward,
        windows=(),
    )

    report = StrategyResearchReporter().build(
        backtest,
        walk_forward,
    )

    assert report.verdict == "INCONCLUSIVE"


def test_report_is_inconclusive_when_windows_are_balanced():

    backtest = _backtest()

    walk_forward = _manual_walk_forward(
        strategy_return=30.0,
        buy_and_hold_return=20.0,
        positive=2,
        negative=2,
    )

    report = StrategyResearchReporter().build(
        backtest,
        walk_forward,
    )

    assert report.verdict == "INCONCLUSIVE"


def test_report_contains_core_metrics():

    backtest = _backtest()

    walk_forward = _manual_walk_forward(
        strategy_return=25.0,
        buy_and_hold_return=15.0,
        positive=3,
        negative=1,
    )

    report = StrategyResearchReporter().build(
        backtest,
        walk_forward,
    )

    assert report.strategy_name == "Trend Following"
    assert report.trade_count == 10
    assert report.win_rate_percent == 60.0
    assert report.max_drawdown_percent == -10.0
    assert report.total_windows == 4


def test_report_formatter_contains_verdict():

    backtest = _backtest()

    walk_forward = _manual_walk_forward(
        strategy_return=25.0,
        buy_and_hold_return=15.0,
        positive=3,
        negative=1,
    )

    report = StrategyResearchReporter().build(
        backtest,
        walk_forward,
    )

    text = format_research_report(
        report
    )

    assert "ATLAS Strategy Research" in text
    assert "Trend Following" in text
    assert "Strategy return" in text
    assert "Buy & Hold return" in text
    assert "VERDICT: EDGE" in text


def test_report_does_not_create_trade_decision():

    backtest = _backtest()

    walk_forward = _manual_walk_forward(
        strategy_return=25.0,
        buy_and_hold_return=15.0,
        positive=3,
        negative=1,
    )

    report = StrategyResearchReporter().build(
        backtest,
        walk_forward,
    )

    assert not hasattr(
        report,
        "decision",
    )

    assert not hasattr(
        report,
        "action",
    )

    assert not hasattr(
        report,
        "buy",
    )

    assert not hasattr(
        report,
        "sell",
    )
