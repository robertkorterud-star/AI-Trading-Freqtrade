from atlas.models.action import Action
from atlas.trading.backtest_result import BacktestResult
from atlas.trading.strategy_hypothesis import StrategyHypothesis
from atlas.services.adaptive_strategy_research_service import (
    AdaptiveStrategyResearchService,
)
from atlas.services.strategy_research_service import (
    StrategyResearchResult,
)
from atlas.trading.backtest_evaluator import (
    BacktestAssessment,
)


def test_adaptive_research_runs_one_followup_round():

    initial_strategy = StrategyHypothesis(
        name="RSI Oversold Reversal",
        symbol="XRP-USD",
        timeframe="15m",
        entry_rule="RSI < 30",
        exit_rule="RSI > 50",
        stop_loss="2%",
        take_profit="4%",
        source="Google News",
        reasoning=[],
    )

    alternative_strategy = StrategyHypothesis(
        name="Moving Average Crossover",
        symbol="XRP-USD",
        timeframe="1h",
        entry_rule="MA20 crosses above MA50",
        exit_rule="MA20 crosses below MA50",
        stop_loss="3%",
        take_profit="6%",
        source="Google News",
        reasoning=[],
    )

    initial_result = StrategyResearchResult(
        symbol="XRP-USD",
        strategies=[initial_strategy],
        backtests=[
            BacktestResult(
                strategy_name="RSI Oversold Reversal",
                symbol="XRP-USD",
                trades=100,
                wins=40,
                losses=60,
                win_rate=40.0,
                total_return=-20.0,
                profit_factor=0.7,
                max_drawdown=30.0,
            )
        ],
        assessments=[
            BacktestAssessment(
                status="REJECT",
                reason="Bad strategy.",
                next_focus=(
                    "moving average",
                    "breakout",
                ),
            )
        ],
    )

    final_result = StrategyResearchResult(
        symbol="XRP-USD",
        strategies=[alternative_strategy],
        backtests=[],
        assessments=[],
    )

    class FakeStrategyResearch:
        def __init__(self):
            self.calls = []

        def research(self, symbol, research):
            self.calls.append(research)

            if len(self.calls) == 1:
                return initial_result

            return final_result

    class FakeWebResearch:
        def __init__(self):
            self.focus = None

        def search(self, symbol, focus=None):
            self.focus = focus

            return [
                {
                    "source": "Google News",
                    "title": "XRP golden cross breakout",
                    "summary": "XRP moving average breakout.",
                }
            ]

    strategy_research = FakeStrategyResearch()
    web_research = FakeWebResearch()

    service = AdaptiveStrategyResearchService(
        strategy_research=strategy_research,
        web_research=web_research,
    )

    result = service.research(
        "XRP-USD",
        [
            {
                "source": "Google News",
                "title": "XRP RSI oversold",
                "summary": "XRP RSI is oversold.",
            }
        ],
    )

    assert result.strategies[0].name == (
        "Moving Average Crossover"
    )

    assert web_research.focus == (
        "moving average",
        "breakout",
    )

    assert len(strategy_research.calls) == 2


def test_adaptive_research_stops_early_when_strategy_passes():

    class FakeStrategyResearch:

        def __init__(self):
            self.calls = []

        def research(self, symbol, research):

            self.calls.append(research)

            if len(self.calls) == 1:
                return StrategyResearchResult(
                    symbol=symbol,
                    strategies=[
                        StrategyHypothesis(
                            name="RSI Oversold Reversal",
                            symbol=symbol,
                            timeframe="15m",
                            entry_rule="RSI < 30",
                            exit_rule="RSI > 50",
                            stop_loss="2%",
                            take_profit="4%",
                            source="Google News",
                            reasoning=[],
                        )
                    ],
                    backtests=[],
                    assessments=[
                        BacktestAssessment(
                            status="REJECT",
                            reason="RSI failed.",
                            next_focus=(
                                "moving average",
                            ),
                        )
                    ],
                )

            if len(self.calls) == 2:
                return StrategyResearchResult(
                    symbol=symbol,
                    strategies=[
                        StrategyHypothesis(
                            name="Moving Average Crossover",
                            symbol=symbol,
                            timeframe="1h",
                            entry_rule="MA20 crosses above MA50",
                            exit_rule="MA20 crosses below MA50",
                            stop_loss="3%",
                            take_profit="6%",
                            source="Google News",
                            reasoning=[],
                        )
                    ],
                    backtests=[],
                    assessments=[
                        BacktestAssessment(
                            status="REJECT",
                            reason="Moving average failed.",
                            next_focus=(
                                "breakout",
                            ),
                        )
                    ],
                )

            return StrategyResearchResult(
                symbol=symbol,
                strategies=[
                    StrategyHypothesis(
                        name="Breakout Strategy",
                        symbol=symbol,
                        timeframe="1h",
                        entry_rule="Price breaks resistance",
                        exit_rule="Price loses breakout level",
                        stop_loss="3%",
                        take_profit="6%",
                        source="Google News",
                        reasoning=[],
                    )
                ],
                backtests=[],
                assessments=[
                    BacktestAssessment(
                        status="PASS",
                        reason="Breakout passed.",
                    )
                ],
            )

    class FakeWebResearch:

        def __init__(self):
            self.focus_calls = []

        def search(self, symbol, focus=None):

            self.focus_calls.append(focus)

            return [
                {
                    "source": "Google News",
                    "title": "Strategy research",
                    "summary": "Strategy signal.",
                }
            ]

    strategy_research = FakeStrategyResearch()
    web_research = FakeWebResearch()

    service = AdaptiveStrategyResearchService(
        strategy_research=strategy_research,
        web_research=web_research,
    )

    result = service.research(
        "XRP-USD",
        [
            {
                "source": "Google News",
                "title": "Initial research",
                "summary": "Initial strategy.",
            }
        ],
    )

    assert len(strategy_research.calls) == 3
    assert len(web_research.focus_calls) == 2
    assert web_research.focus_calls[0] == (
        "moving average",
    )
    assert web_research.focus_calls[1] == (
        "breakout",
    )
    assert result.assessments[0].status == "PASS"
    assert len(result.history) == 3
