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
