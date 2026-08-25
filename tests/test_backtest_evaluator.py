from atlas.trading.backtest_evaluator import (
    BacktestEvaluator,
)


def test_backtest_evaluator_rejects_negative_return():

    result = type(
        "BacktestResult",
        (),
        {
            "trades": 230,
            "wins": 130,
            "losses": 100,
            "win_rate": 56.52,
            "total_return": -38.64,
            "profit_factor": 0.82,
            "max_drawdown": 40.88,
        },
    )()

    assessment = BacktestEvaluator.assess(
        result
    )

    assert assessment.status == "REJECT"
    assert assessment.reason


def test_backtest_evaluator_passes_strong_result():

    result = type(
        "BacktestResult",
        (),
        {
            "trades": 180,
            "wins": 110,
            "losses": 70,
            "win_rate": 61.11,
            "total_return": 24.8,
            "profit_factor": 1.34,
            "max_drawdown": 12.4,
        },
    )()

    assessment = BacktestEvaluator.assess(
        result
    )

    assert assessment.status == "PASS"
    assert assessment.reason


def test_backtest_evaluator_marks_borderline_result_inconclusive():

    result = type(
        "BacktestResult",
        (),
        {
            "trades": 80,
            "wins": 45,
            "losses": 35,
            "win_rate": 56.25,
            "total_return": 3.0,
            "profit_factor": 1.03,
            "max_drawdown": 24.0,
        },
    )()

    assessment = BacktestEvaluator.assess(
        result
    )

    assert assessment.status == "INCONCLUSIVE"
    assert assessment.reason
