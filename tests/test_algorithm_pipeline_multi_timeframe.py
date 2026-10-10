import pytest

from atlas.algorithms.base import AlgorithmSignal
from atlas.algorithms.pipeline import AlgorithmPipeline
from atlas.algorithms.registry import AlgorithmRegistry
from atlas.models.action import Action
from atlas.trading.market_data import Candle, MarketSnapshot


class TimeframeAlgorithm:
    def __init__(self, timeframe, action):
        self.name = f"test_{timeframe}"
        self.timeframe = timeframe
        self.action = action

    def generate_signal(self, symbol, candles):
        return AlgorithmSignal(
            algorithm=self.name,
            symbol=symbol,
            timeframe=self.timeframe,
            action=self.action,
            score=80.0 if self.action is Action.BUY else 50.0,
            confidence=0.8,
        )


def test_pipeline_keeps_timeframe_fusion_separate():
    def candle(timestamp):
        return Candle(
            timestamp=timestamp,
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=10.0,
        )

    snapshot = MarketSnapshot.from_candles(
        "BTC-USD",
        [candle(1000.0)],
        timeframe="5m",
        timeframe_candles={
            "5m": [candle(1000.0)],
            "15m": [candle(900.0)],
        },
    )

    registry = AlgorithmRegistry()
    registry.register(TimeframeAlgorithm("5m", Action.BUY))
    registry.register(TimeframeAlgorithm("15m", Action.HOLD))

    pipeline = AlgorithmPipeline(registry)

    # The existing single-timeframe analyze contract must not
    # silently mix evidence from different candle intervals.
    with pytest.raises(
        ValueError,
        match="all signals must use the same timeframe",
    ):
        pipeline.analyze("BTC-USD", snapshot)


def test_pipeline_analyzes_each_timeframe_independently():
    def candle(timestamp):
        return Candle(
            timestamp=timestamp,
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=10.0,
        )

    snapshot = MarketSnapshot.from_candles(
        "BTC-USD",
        [candle(1000.0)],
        timeframe="5m",
        timeframe_candles={
            "5m": [candle(1000.0)],
            "15m": [candle(900.0)],
        },
    )

    registry = AlgorithmRegistry()
    registry.register(TimeframeAlgorithm("5m", Action.BUY))
    registry.register(TimeframeAlgorithm("15m", Action.HOLD))

    pipeline = AlgorithmPipeline(registry)

    results = pipeline.analyze_timeframes("BTC-USD", snapshot)

    assert set(results) == {"5m", "15m"}
    assert results["5m"].action is Action.BUY
    assert results["15m"].action is Action.HOLD
    assert results["5m"].timeframe == "5m"
    assert results["15m"].timeframe == "15m"
