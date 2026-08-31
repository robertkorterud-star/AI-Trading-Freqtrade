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
