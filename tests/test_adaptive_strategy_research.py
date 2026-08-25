from atlas.agents.strategy_learning_agent import (
    StrategyLearningAgent,
)
from atlas.trading.backtest_evaluator import (
    BacktestEvaluator,
)


def test_rejected_rsi_strategy_produces_next_research_focus():

    result = type(
        "BacktestResult",
        (),
        {
            "total_return": -38.64,
            "profit_factor": 0.82,
            "max_drawdown": 40.88,
        },
    )()

    assessment = BacktestEvaluator.assess(
        result,
        strategy_name="RSI Oversold Reversal",
    )

    assert assessment.status == "REJECT"
    assert "moving average" in (
        assessment.next_focus
    )
    assert "breakout" in (
        assessment.next_focus
    )


def test_next_focus_can_generate_alternative_strategy():

    agent = StrategyLearningAgent()

    research = [
        {
            "source": "Google News",
            "title": (
                "XRP completes golden cross "
                "and breakout signal"
            ),
            "summary": (
                "XRP golden cross suggests "
                "a possible breakout."
            ),
        }
    ]

    strategies = agent.learn(
        "XRP-USD",
        research,
    )

    assert strategies
    assert any(
        strategy.name
        == "Moving Average Crossover"
        for strategy in strategies
    )
