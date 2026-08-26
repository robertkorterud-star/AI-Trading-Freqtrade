"""
Strategy Research Service

Connects intelligence research, strategy discovery,
historical market data and backtesting.

This service does NOT place trades.
"""

from dataclasses import dataclass, field

from atlas.adapters.historical_market_data import (
    HistoricalMarketDataAdapter,
)
from atlas.trading.backtest_engine import BacktestEngine
from atlas.trading.backtest_result import BacktestResult
from atlas.trading.backtest_evaluator import (
    BacktestAssessment,
    BacktestEvaluator,
)
from atlas.trading.indicators import (
    calculate_rsi,
    calculate_sma,
)
from atlas.trading.strategy_hypothesis import (
    StrategyHypothesis,
)
from atlas.trading.timing_analysis import (
    TimingOpportunity,
    TimingAnalyzer,
)
from atlas.agents.strategy_learning_agent import (
    StrategyLearningAgent,
)


@dataclass(slots=True)
class StrategyResearchResult:
    symbol: str
    strategies: list[StrategyHypothesis]
    backtests: list[BacktestResult]
    assessments: list[BacktestAssessment]
    timing: list[TimingOpportunity] = field(
        default_factory=list
    )
    history: list["StrategyResearchResult"] = field(
        default_factory=list
    )


class StrategyResearchService:
    """Runs the complete strategy research pipeline."""

    def __init__(
        self,
        strategy_agent=None,
        market_data=None,
        backtest_engine=None,
    ) -> None:

        self.strategy_agent = (
            strategy_agent
            if strategy_agent is not None
            else StrategyLearningAgent()
        )

        self.market_data = (
            market_data
            if market_data is not None
            else HistoricalMarketDataAdapter()
        )

        self.backtest_engine = (
            backtest_engine
            if backtest_engine is not None
            else BacktestEngine()
        )

        self.timing_analyzer = TimingAnalyzer()

    def research(
        self,
        symbol: str,
        research: list[dict],
    ) -> StrategyResearchResult:
        """Discover strategies and backtest them."""

        strategies = self.strategy_agent.learn(
            symbol,
            research,
        )

        if not strategies:
            return StrategyResearchResult(
                symbol=symbol,
                strategies=[],
                backtests=[],
                assessments=[],
            )

        candles = self.market_data.get(
            symbol,
            period="1y",
            interval="1h",
        )

        if not candles:
            return StrategyResearchResult(
                symbol=symbol,
                strategies=strategies,
                backtests=[],
                assessments=[],
            )

        closes = [
            candle["close"]
            for candle in candles
        ]

        rsi_values = calculate_rsi(closes)
        ma20_values = calculate_sma(
            closes,
            period=20,
        )
        ma50_values = calculate_sma(
            closes,
            period=50,
        )

        enriched_candles = []

        for candle, rsi, ma20, ma50 in zip(
            candles,
            rsi_values,
            ma20_values,
            ma50_values,
        ):
            enriched = dict(candle)
            enriched["rsi"] = rsi
            enriched["ma20"] = ma20
            enriched["ma50"] = ma50
            enriched_candles.append(enriched)

        backtests = []
        assessments = []
        timing = []

        for strategy in strategies:

            result = self.backtest_engine.run(
                strategy,
                enriched_candles,
            )

            backtests.append(result)

            assessments.append(
                BacktestEvaluator.assess(
                    result,
                    strategy_name=strategy.name,
                )
            )

            timing.append(
                self.timing_analyzer.analyze(
                    strategy,
                    enriched_candles,
                )
            )

        return StrategyResearchResult(
            symbol=symbol,
            strategies=strategies,
            backtests=backtests,
            assessments=assessments,
            timing=timing,
        )
