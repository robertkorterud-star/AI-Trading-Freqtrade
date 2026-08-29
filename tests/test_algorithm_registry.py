import pytest

from atlas.algorithms.base import AlgorithmSignal
from atlas.algorithms.momentum import IntradayMomentumAlgorithm
from atlas.algorithms.registry import AlgorithmRegistry
from atlas.models.action import Action


class StubAlgorithm:
    name = "stub"
    timeframe = "5m"

    def __init__(self, action=Action.HOLD):
        self.action = action
        self.calls = 0

    def generate_signal(self, symbol, candles):
        self.calls += 1

        return AlgorithmSignal(
            algorithm=self.name,
            symbol=symbol,
            timeframe=self.timeframe,
            action=self.action,
            score=50.0,
            confidence=50.0,
            expected_edge=None,
            reasoning=["stub"],
        )


def test_registry_starts_empty():
    registry = AlgorithmRegistry()

    assert registry.names() == ()
    assert registry.all() == ()


def test_registry_registers_and_retrieves_algorithm():
    registry = AlgorithmRegistry()
    algorithm = IntradayMomentumAlgorithm()

    registry.register(algorithm)

    assert registry.get("intraday_momentum") is algorithm
    assert registry.names() == ("intraday_momentum",)
    assert registry.all() == (algorithm,)


def test_registry_rejects_duplicate_algorithm_name():
    registry = AlgorithmRegistry()

    registry.register(StubAlgorithm())

    with pytest.raises(
        ValueError,
        match="algorithm already registered: stub",
    ):
        registry.register(StubAlgorithm())


def test_registry_rejects_unknown_algorithm():
    registry = AlgorithmRegistry()

    with pytest.raises(
        KeyError,
        match="algorithm not registered: missing",
    ):
        registry.get("missing")


def test_registry_generates_signals_from_all_algorithms():
    registry = AlgorithmRegistry()

    first = StubAlgorithm(Action.BUY)
    second = StubAlgorithm(Action.SELL)

    second.name = "second_stub"

    registry.register(first)
    registry.register(second)

    signals = registry.generate_signals(
        "BTC-USD",
        [{"close": 100.0}],
    )

    assert len(signals) == 2
    assert all(isinstance(signal, AlgorithmSignal) for signal in signals)

    assert signals[0].algorithm == "stub"
    assert signals[0].action is Action.BUY

    assert signals[1].algorithm == "second_stub"
    assert signals[1].action is Action.SELL

    assert first.calls == 1
    assert second.calls == 1


def test_registry_preserves_registration_order():
    registry = AlgorithmRegistry()

    first = StubAlgorithm()
    second = StubAlgorithm()
    second.name = "second_stub"

    registry.register(first)
    registry.register(second)

    assert registry.names() == (
        "stub",
        "second_stub",
    )


def test_registry_supports_mean_reversion_algorithm():
    from atlas.algorithms.mean_reversion import (
        IntradayMeanReversionAlgorithm,
    )

    registry = AlgorithmRegistry()
    algorithm = IntradayMeanReversionAlgorithm()

    registry.register(algorithm)

    assert registry.get(
        "intraday_mean_reversion"
    ) is algorithm


def test_registry_supports_breakout_algorithm():
    from atlas.algorithms.breakout import (
        IntradayBreakoutAlgorithm,
    )

    registry = AlgorithmRegistry()
    algorithm = IntradayBreakoutAlgorithm()

    registry.register(algorithm)

    assert registry.get(
        "intraday_breakout"
    ) is algorithm


def test_registry_supports_vwap_algorithm():
    from atlas.algorithms.vwap import (
        IntradayVWAPAlgorithm,
    )

    registry = AlgorithmRegistry()
    algorithm = IntradayVWAPAlgorithm()

    registry.register(algorithm)

    assert registry.get(
        "intraday_vwap"
    ) is algorithm
