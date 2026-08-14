from atlas.agents.strategy_learning_agent import (
    StrategyLearningAgent,
)


def test_strategy_agent_extracts_rsi_strategy():

    research = [
        {
            "source": "YouTube",
            "title": "RSI oversold strategy",
            "summary": "Buy when RSI falls below 30.",
        }
    ]

    agent = StrategyLearningAgent()

    hypotheses = agent.learn(
        "NVDA",
        research,
    )

    assert len(hypotheses) == 1

    strategy = hypotheses[0]

    assert strategy.name == "RSI Oversold Reversal"
    assert strategy.symbol == "NVDA"
    assert strategy.entry_rule == "RSI < 30"
    assert strategy.source == "YouTube"


def test_strategy_agent_extracts_ma_strategy():

    research = [
        {
            "source": "Finnhub",
            "title": "Moving average crossover",
            "summary": "A golden cross can indicate momentum.",
        }
    ]

    agent = StrategyLearningAgent()

    hypotheses = agent.learn(
        "NVDA",
        research,
    )

    assert len(hypotheses) == 1

    strategy = hypotheses[0]

    assert strategy.name == "Moving Average Crossover"
    assert strategy.timeframe == "1h"
    assert strategy.entry_rule == (
        "MA20 crosses above MA50"
    )


def test_strategy_agent_ignores_irrelevant_research():

    research = [
        {
            "source": "Reuters",
            "title": "NVIDIA announces new product",
            "summary": "The company introduced a new chip.",
        }
    ]

    agent = StrategyLearningAgent()

    hypotheses = agent.learn(
        "NVDA",
        research,
    )

    assert hypotheses == []
