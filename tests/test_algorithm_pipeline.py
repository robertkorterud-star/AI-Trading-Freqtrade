from atlas.algorithms.pipeline import AlgorithmPipeline
from atlas.algorithms.registry import AlgorithmRegistry


class StubAlgorithm:
    def __init__(self, name, action="BUY"):
        self.name = name
        self.action = action

    def generate_signal(self, symbol, market_data):
        from atlas.algorithms.base import Action, AlgorithmSignal

        return AlgorithmSignal(
            algorithm=self.name,
            symbol=symbol,
            timeframe="multi",
            action=Action[self.action],
            score=0.8,
            confidence=0.9,
        )


def test_pipeline_generates_signals_from_registered_algorithms():
    registry = AlgorithmRegistry()

    registry.register(StubAlgorithm("momentum"))
    registry.register(StubAlgorithm("trend"))
    registry.register(StubAlgorithm("breakout"))
    registry.register(StubAlgorithm("mean_reversion"))
    registry.register(StubAlgorithm("vwap"))

    pipeline = AlgorithmPipeline(registry)

    signals = pipeline.generate_signals(
        "BTC-USD",
        {"price": 100.0, "candles": []},
    )

    assert len(signals) == 5
    assert {signal.algorithm for signal in signals} == {
        "momentum",
        "trend",
        "breakout",
        "mean_reversion",
        "vwap",
    }


def test_pipeline_fuses_registered_algorithm_signals():
    registry = AlgorithmRegistry()

    registry.register(StubAlgorithm("momentum"))
    registry.register(StubAlgorithm("trend"))

    pipeline = AlgorithmPipeline(registry)

    fused, signals = pipeline.analyze(
        "BTC-USD",
        {"price": 100.0, "candles": []},
    )

    assert len(signals) == 2
    assert fused is not None

def test_pipeline_analyze_returns_fused_action_and_signals():
    registry = AlgorithmRegistry()

    registry.register(StubAlgorithm("momentum", action="BUY"))
    registry.register(StubAlgorithm("trend", action="BUY"))
    registry.register(StubAlgorithm("breakout", action="HOLD"))

    pipeline = AlgorithmPipeline(registry)

    fused, signals = pipeline.analyze(
        "BTC-USD",
        {"price": 100.0, "candles": []},
    )

    assert fused is not None
    assert fused.symbol == "BTC-USD"
    assert fused.action.value == "BUY"
    assert fused.signals == tuple(signals)
    assert fused.agreement == 0.6667


def test_pipeline_analyze_returns_none_for_empty_registry():
    registry = AlgorithmRegistry()
    pipeline = AlgorithmPipeline(registry)

    fused, signals = pipeline.analyze(
        "BTC-USD",
        {"price": 100.0, "candles": []},
    )

    assert fused is None
    assert signals == []


def test_pipeline_fusion_preserves_all_algorithm_signals():
    registry = AlgorithmRegistry()

    registry.register(StubAlgorithm("momentum", action="BUY"))
    registry.register(StubAlgorithm("trend", action="SELL"))
    registry.register(StubAlgorithm("breakout", action="HOLD"))

    pipeline = AlgorithmPipeline(registry)

    fused, signals = pipeline.analyze(
        "BTC-USD",
        {"price": 100.0, "candles": []},
    )

    assert fused is not None
    assert len(fused.signals) == 3
    assert [signal.algorithm for signal in fused.signals] == [
        "momentum",
        "trend",
        "breakout",
    ]
    assert fused.action.value == "HOLD"


def test_pipeline_skips_algorithm_with_insufficient_history():
    class ShortHistoryAlgorithm:
        name = "short_history"
        timeframe = "5m"

        def generate_signal(self, symbol, candles):
            raise ValueError("at least 24 candles are required")

    class WorkingAlgorithm:
        name = "working"
        timeframe = "5m"

        def generate_signal(self, symbol, candles):
            from atlas.algorithms.base import AlgorithmSignal
            from atlas.models.action import Action

            return AlgorithmSignal(
                algorithm=self.name,
                symbol=symbol,
                timeframe=self.timeframe,
                action=Action.HOLD,
                score=50.0,
                confidence=50.0,
            )

    registry = AlgorithmRegistry()
    registry.register(ShortHistoryAlgorithm())
    registry.register(WorkingAlgorithm())

    pipeline = AlgorithmPipeline(registry)

    signals = pipeline.generate_signals(
        "BTC-USD",
        {"candles": [{"close": 100.0}]},
    )

    assert len(signals) == 1
    assert signals[0].algorithm == "working"


def test_pipeline_does_not_hide_unrelated_value_errors():
    class BrokenAlgorithm:
        name = "broken"
        timeframe = "5m"

        def generate_signal(self, symbol, candles):
            raise ValueError(
                "candles must contain finite positive close prices"
            )

    registry = AlgorithmRegistry()
    registry.register(BrokenAlgorithm())

    pipeline = AlgorithmPipeline(registry)

    import pytest

    with pytest.raises(
        ValueError,
        match="candles must contain finite positive close prices",
    ):
        pipeline.generate_signals(
            "BTC-USD",
            {"candles": [{"close": -1.0}]},
        )


def test_pipeline_uses_candles_matching_each_algorithm_timeframe():
    from atlas.trading.market_data import Candle, MarketSnapshot

    class CapturingAlgorithm:
        def __init__(self, name, timeframe):
            self.name = name
            self.timeframe = timeframe
            self.received_candles = None

        def generate_signal(self, symbol, candles):
            from atlas.algorithms.base import AlgorithmSignal
            from atlas.models.action import Action

            self.received_candles = candles
            return AlgorithmSignal(
                algorithm=self.name,
                symbol=symbol,
                timeframe=self.timeframe,
                action=Action.HOLD,
                score=50.0,
                confidence=50.0,
            )

    def candle(timestamp, close):
        return Candle(
            timestamp=timestamp,
            open=close,
            high=close,
            low=close,
            close=close,
            volume=1.0,
        )

    base = (candle(1.0, 100.0),)
    five_minute = (candle(2.0, 101.0),)
    fifteen_minute = (candle(3.0, 102.0),)

    snapshot = MarketSnapshot.from_candles(
        "BTC-USD",
        base,
        timeframe_candles={
            "5m": five_minute,
            "15m": fifteen_minute,
        },
    )

    five = CapturingAlgorithm("five", "5m")
    fifteen = CapturingAlgorithm("fifteen", "15m")

    registry = AlgorithmRegistry()
    registry.register(five)
    registry.register(fifteen)

    signals = AlgorithmPipeline(registry).generate_signals(
        "BTC-USD",
        snapshot,
    )

    assert len(signals) == 2
    assert five.received_candles == five_minute
    assert fifteen.received_candles == fifteen_minute


def test_pipeline_does_not_substitute_base_candles_for_missing_explicit_timeframe():
    from atlas.trading.market_data import Candle, MarketSnapshot

    class CapturingAlgorithm:
        name = "five_minute_only"
        timeframe = "5m"

        def __init__(self):
            self.calls = []

        def generate_signal(self, symbol, candles):
            self.calls.append((symbol, candles))
            raise AssertionError(
                "5m algorithm must not receive fallback base candles"
            )

    def candle(timestamp, close):
        return Candle(
            timestamp=timestamp,
            open=close,
            high=close,
            low=close,
            close=close,
            volume=1.0,
        )

    daily = (candle(1.0, 100.0),)
    hourly = (candle(2.0, 101.0),)

    snapshot = MarketSnapshot.from_candles(
        "NVDA",
        daily,
        timeframe_candles={
            "1h": hourly,
        },
    )

    algorithm = CapturingAlgorithm()
    registry = AlgorithmRegistry()
    registry.register(algorithm)

    signals = AlgorithmPipeline(registry).generate_signals(
        "NVDA",
        snapshot,
    )

    assert signals == []
    assert algorithm.calls == []


def test_pipeline_uses_base_candles_when_algorithm_matches_snapshot_timeframe():
    """Explicit algorithm timeframe may use base candles only when it matches the snapshot."""
    from atlas.trading.market_data import Candle, MarketSnapshot

    class CapturingAlgorithm:
        name = "five_minute"
        timeframe = "5m"

        def __init__(self):
            self.received_candles = None

        def generate_signal(self, symbol, candles):
            from atlas.algorithms.base import AlgorithmSignal
            from atlas.models.action import Action

            self.received_candles = candles
            return AlgorithmSignal(
                algorithm=self.name,
                symbol=symbol,
                timeframe=self.timeframe,
                action=Action.HOLD,
                score=50.0,
                confidence=50.0,
            )

    def candle(timestamp, close):
        return Candle(
            timestamp=timestamp,
            open=close,
            high=close,
            low=close,
            close=close,
            volume=1.0,
        )

    base = (
        candle(1.0, 100.0),
        candle(2.0, 101.0),
    )
    fifteen_minute = (
        candle(3.0, 102.0),
    )

    snapshot = MarketSnapshot.from_candles(
        "BTCUSDT",
        base,
        timeframe="5m",
        timeframe_candles={
            "15m": fifteen_minute,
        },
    )

    algorithm = CapturingAlgorithm()
    registry = AlgorithmRegistry()
    registry.register(algorithm)

    signals = AlgorithmPipeline(registry).generate_signals(
        "BTCUSDT",
        snapshot,
    )

    assert len(signals) == 1
    assert algorithm.received_candles == base
