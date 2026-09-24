from atlas.agents import (
    MomentumAgent,
    TrendAgent,
    VolumeAgent,
    VolatilityAgent,
)
from atlas.trading.dry_run_loop import DryRunLoop
from atlas.trading.market_data import Candle, MarketSnapshot


def snapshot():
    return MarketSnapshot(
        symbol="BTC-USD",
        timestamp=4,
        price=108.0,
        candles=tuple(
            Candle(
                timestamp=i,
                open=100 + (i - 1) * 0.15,
                high=101 + (i - 1) * 0.15,
                low=99 + (i - 1) * 0.15,
                close=100 + (i - 1) * 0.15,
                volume=1000 + i * 100,
            )
            for i in range(1, 23)
        ) + (
            Candle(
                timestamp=23,
                open=103,
                high=105,
                low=102,
                close=108.0,
                volume=3300,
            ),
        ),
    )


def agents():
    return [
        TrendAgent(),
        MomentumAgent(),
        VolumeAgent(),
        VolatilityAgent(),
    ]


def test_complete_atlas_pipeline_runs_end_to_end():
    loop = DryRunLoop(agents=agents())

    result = loop.process(snapshot())

    assert result.symbol == "BTC-USD"
    assert result.price == 108.0

    assert len(result.observations) == 4

    assert -1.0 <= result.intelligence_score <= 1.0
    assert 0.0 <= result.intelligence_confidence <= 1.0

    assert result.decision is not None
    assert result.execution is not None

    assert result.execution.symbol == "BTC-USD"
    assert result.execution.price == 108.0


def test_pipeline_preserves_all_agent_observations():
    loop = DryRunLoop(agents=agents())

    result = loop.process(snapshot())

    names = {
        observation.agent
        for observation in result.observations
    }

    assert names == {
        "trend",
        "momentum",
        "volume",
        "volatility",
    }


def test_pipeline_produces_a_valid_final_decision():
    loop = DryRunLoop(agents=agents())

    result = loop.process(snapshot())

    decision = result.decision

    assert decision.action is not None
    assert -1.0 <= decision.score <= 1.0
    assert 0.0 <= decision.confidence <= 1.0
    assert 0.0 <= decision.risk_score <= 1.0
    assert decision.reason


def test_pipeline_execution_is_paper_only():
    loop = DryRunLoop(agents=agents())

    result = loop.process(snapshot())

    trader = loop.trader

    assert result.execution.equity > 0.0
    assert trader.portfolio.cash >= 0.0

    assert not hasattr(trader, "exchange")
    assert not hasattr(trader, "ccxt")


def test_pipeline_can_process_multiple_cycles():
    loop = DryRunLoop(agents=agents())

    first = loop.process(snapshot())

    second_snapshot = MarketSnapshot(
        symbol="BTC-USD",
        timestamp=5,
        price=112.0,
        candles=(
            *snapshot().candles,
            Candle(
                timestamp=24,
                open=108,
                high=113,
                low=107,
                close=112,
                volume=1900,
            ),
        ),
    )

    second = loop.process(second_snapshot)

    assert first.symbol == second.symbol == "BTC-USD"
    assert second.price == 112.0
    assert second.execution.equity > 0.0


def test_dry_run_loop_routes_snapshot_timeframes_to_algorithms():
    from atlas.algorithms import AlgorithmSignal
    from atlas.algorithms.pipeline import AlgorithmPipeline
    from atlas.algorithms.registry import AlgorithmRegistry
    from atlas.models.action import Action

    class CapturingAlgorithm:
        name = "capturing"
        timeframe = "5m"

        def __init__(self):
            self.received_candles = None

        def generate_signal(self, symbol, candles):
            self.received_candles = candles
            return AlgorithmSignal(
                algorithm=self.name,
                symbol=symbol,
                timeframe=self.timeframe,
                action=Action.HOLD,
                score=50.0,
                confidence=50.0,
            )

    algorithm = CapturingAlgorithm()
    registry = AlgorithmRegistry()
    registry.register(algorithm)

    base = snapshot()
    five_minute = tuple(
        Candle(
            timestamp=candle.timestamp,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume + 1,
        )
        for candle in base.candles
    )

    multi_timeframe_snapshot = MarketSnapshot(
        symbol=base.symbol,
        timestamp=base.timestamp,
        price=base.price,
        candles=base.candles,
        timeframe_candles={"5m": five_minute},
    )

    loop = DryRunLoop(
        agents=agents(),
        algorithm_pipeline=AlgorithmPipeline(registry),
    )

    loop.process(multi_timeframe_snapshot)

    assert algorithm.received_candles == five_minute
