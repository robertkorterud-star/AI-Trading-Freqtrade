from atlas.services.strategy_research_service import (
    StrategyResearchService,
)
from atlas.trading.backtest_result import BacktestResult
from atlas.trading.strategy_hypothesis import (
    StrategyHypothesis,
)


class FakeStrategyAgent:

    def learn(self, symbol, research):

        return [
            StrategyHypothesis(
                name="RSI Oversold Reversal",
                symbol=symbol,
                timeframe="15m",
                entry_rule="RSI < 30",
                exit_rule="RSI > 50",
                stop_loss="2%",
                take_profit="4%",
                source="YouTube",
            )
        ]


class FakeMarketData:

    def get(self, symbol, period, interval):

        return [
            {
                "timestamp": "1",
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100,
                "volume": 1000,
            },
            {
                "timestamp": "2",
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 101,
                "volume": 1000,
            },
        ]


class FakeBacktestEngine:

    def run(self, strategy, candles):

        return BacktestResult(
            strategy_name=strategy.name,
            symbol=strategy.symbol,
            trades=10,
            wins=6,
            losses=4,
            win_rate=60.0,
            total_return=12.0,
            profit_factor=1.5,
            max_drawdown=5.0,
        )


def test_strategy_research_connects_pipeline():

    service = StrategyResearchService(
        strategy_agent=FakeStrategyAgent(),
        market_data=FakeMarketData(),
        backtest_engine=FakeBacktestEngine(),
    )

    result = service.research(
        "NVDA",
        [
            {
                "source": "YouTube",
                "title": "RSI strategy",
                "summary": "Buy when RSI is oversold.",
            }
        ],
    )

    assert result.symbol == "NVDA"
    assert len(result.strategies) == 1
    assert len(result.backtests) == 1

    assert (
        result.backtests[0].strategy_name
        == "RSI Oversold Reversal"
    )

    assert result.backtests[0].win_rate == 60.0


def test_strategy_research_handles_no_strategies():

    class EmptyAgent:

        def learn(self, symbol, research):
            return []

    service = StrategyResearchService(
        strategy_agent=EmptyAgent(),
        market_data=FakeMarketData(),
        backtest_engine=FakeBacktestEngine(),
    )

    result = service.research(
        "NVDA",
        [],
    )

    assert result.symbol == "NVDA"
    assert result.strategies == []
    assert result.backtests == []


def test_strategy_research_handles_no_market_data():

    class EmptyMarketData:

        def get(self, symbol, period, interval):
            return []

    service = StrategyResearchService(
        strategy_agent=FakeStrategyAgent(),
        market_data=EmptyMarketData(),
        backtest_engine=FakeBacktestEngine(),
    )

    result = service.research(
        "NVDA",
        [],
    )

    assert len(result.strategies) == 1
    assert result.backtests == []


def test_strategy_research_enriches_candles_with_moving_averages():

    class InspectingBacktestEngine:

        def __init__(self):
            self.candles = None

        def run(self, strategy, candles):
            self.candles = candles

            return BacktestResult(
                strategy_name=strategy.name,
                symbol=strategy.symbol,
                trades=0,
                wins=0,
                losses=0,
                win_rate=0.0,
                total_return=0.0,
                profit_factor=0.0,
                max_drawdown=0.0,
            )

    market_data = FakeMarketData()
    backtest = InspectingBacktestEngine()

    service = StrategyResearchService(
        strategy_agent=FakeStrategyAgent(),
        market_data=market_data,
        backtest_engine=backtest,
    )

    service.research(
        "NVDA",
        [],
    )

    assert backtest.candles is not None
    assert "rsi" in backtest.candles[0]
    assert "ma20" in backtest.candles[0]
    assert "ma50" in backtest.candles[0]
