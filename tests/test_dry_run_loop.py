from atlas.agents.base import AgentObservation
from atlas.trading.dry_run_loop import DryRunLoop
from atlas.trading.market_data import Candle, MarketSnapshot


class BullishAgent:
    name = "bullish"

    def analyze(self, snapshot):
        return AgentObservation(
            agent=self.name,
            symbol=snapshot.symbol,
            score=0.90,
            confidence=0.90,
            direction="bullish",
            reason="strong bullish test signal",
        )


class BearishAgent:
    name = "bearish"

    def analyze(self, snapshot):
        return AgentObservation(
            agent=self.name,
            symbol=snapshot.symbol,
            score=-0.90,
            confidence=0.90,
            direction="bearish",
            reason="strong bearish test signal",
        )


def snapshot():
    candles = [
        Candle(
            timestamp=i,
            open=100 + (i - 1) * 0.15,
            high=101 + (i - 1) * 0.15,
            low=99 + (i - 1) * 0.15,
            close=100 + (i - 1) * 0.15,
            volume=1000 + i * 100,
        )
        for i in range(1, 23)
    ]

    candles.append(
        Candle(
            timestamp=23,
            open=103,
            high=105,
            low=102,
            close=104,
            volume=3300,
        )
    )

    return MarketSnapshot.from_candles(
        "BTC-USD",
        candles,
    )


def test_dry_run_loop_connects_agents_to_execution():
    loop = DryRunLoop(
        agents=[BullishAgent()],
    )

    result = loop.process(snapshot())

    assert result.symbol == "BTC-USD"
    assert result.price == 104
    assert len(result.observations) == 1
    assert result.intelligence_score > 0
    assert result.execution.symbol == "BTC-USD"


def test_conflicting_agents_reduce_intelligence():
    loop = DryRunLoop(
        agents=[
            BullishAgent(),
            BearishAgent(),
        ],
    )

    result = loop.process(snapshot())

    assert abs(result.intelligence_score) < 0.20


def test_loop_never_uses_live_exchange():
    loop = DryRunLoop(
        agents=[BullishAgent()],
    )

    result = loop.process(snapshot())

    assert result.execution.equity > 0
    assert loop.trader.portfolio.cash > 0


def test_dry_run_loop_uses_algorithm_pipeline():
    from atlas.algorithms.pipeline import AlgorithmPipeline

    loop = DryRunLoop(
        agents=[BullishAgent()],
    )

    assert isinstance(loop.algorithm_pipeline, AlgorithmPipeline)

    result = loop.process(snapshot())

    assert len(result.algorithm_signals) == 5
    assert {
        signal.algorithm
        for signal in result.algorithm_signals
    } == {
        "intraday_momentum",
        "intraday_trend",
        "intraday_breakout",
        "intraday_mean_reversion",
        "intraday_vwap",
    }


def test_dry_run_loop_connects_algorithm_pipeline_to_orchestrator():
    from atlas.algorithms.orchestrator import DecisionOrchestrator
    from atlas.algorithms.pipeline import AlgorithmPipeline

    loop = DryRunLoop(
        agents=[BullishAgent()],
    )

    assert isinstance(loop.algorithm_pipeline, AlgorithmPipeline)
    assert isinstance(loop.orchestrator, DecisionOrchestrator)
    assert loop.orchestrator.algorithm_pipeline is loop.algorithm_pipeline

    result = loop.process(snapshot())

    assert result.algorithm_signals


def test_process_binance_feeds_snapshot_into_dry_run():
    class FakeBinance:
        def get_klines(self, **kwargs):
            return [
                [1710000000000, "100", "101", "99", "100.5", "10"],
                [1710000060000, "100.5", "103", "100", "102", "20"],
            ]

    loop = DryRunLoop(agents=[BullishAgent()])

    result = loop.process_binance(
        FakeBinance(),
        symbol="BTCUSDT",
        interval="1m",
        limit=2,
    )

    assert result.symbol == "BTCUSDT"
    assert result.price == 102.0
    assert result.execution.symbol == "BTCUSDT"
    assert len(result.observations) == 1
