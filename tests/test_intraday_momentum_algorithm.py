import pytest

from atlas.algorithms.base import AlgorithmSignal
from atlas.algorithms.momentum import IntradayMomentumAlgorithm
from atlas.models.action import Action


def candles_from_closes(closes):
    return [
        {
            "timestamp": str(index),
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": 1.0,
        }
        for index, close in enumerate(closes)
    ]


def test_momentum_returns_structured_signal_for_bullish_alignment():
    algorithm = IntradayMomentumAlgorithm()
    candles = candles_from_closes(
        [
            100.0,
            100.1,
            100.2,
            100.3,
            100.4,
            100.5,
            100.6,
            100.7,
            100.8,
            100.9,
            101.0,
            101.1,
            101.2,
        ]
    )

    signal = algorithm.generate_signal("BTC-USD", candles)

    assert isinstance(signal, AlgorithmSignal)
    assert signal.algorithm == "intraday_momentum"
    assert signal.symbol == "BTC-USD"
    assert signal.timeframe == "5m"
    assert signal.action is Action.BUY
    assert 50.0 <= signal.score <= 100.0
    assert 50.0 <= signal.confidence <= 90.0
    assert signal.expected_edge is None
    assert signal.reasoning


def test_momentum_returns_hold_when_directions_do_not_align():
    algorithm = IntradayMomentumAlgorithm()
    candles = candles_from_closes(
        [
            100.0,
            99.0,
            98.0,
            97.0,
            96.0,
            95.0,
            94.0,
            93.0,
            92.0,
            91.0,
            90.0,
            90.1,
            91.5,
        ]
    )

    signal = algorithm.generate_signal("BTC-USD", candles)

    assert signal.action is Action.HOLD
    assert signal.score == 50.0


def test_momentum_returns_sell_for_bearish_alignment():
    algorithm = IntradayMomentumAlgorithm()
    candles = candles_from_closes(
        [
            101.2,
            101.1,
            101.0,
            100.9,
            100.8,
            100.7,
            100.6,
            100.5,
            100.4,
            100.3,
            100.2,
            100.1,
            100.0,
        ]
    )

    signal = algorithm.generate_signal("BTC-USD", candles)

    assert signal.action is Action.SELL
    assert signal.score < 50.0


def test_momentum_requires_enough_candles():
    algorithm = IntradayMomentumAlgorithm()

    with pytest.raises(ValueError, match="at least 13 candles"):
        algorithm.generate_signal(
            "BTC-USD",
            candles_from_closes([100.0] * 12),
        )


def test_momentum_rejects_invalid_close_prices():
    algorithm = IntradayMomentumAlgorithm()
    candles = candles_from_closes([100.0] * 12 + [0.0])

    with pytest.raises(ValueError, match="finite positive close prices"):
        algorithm.generate_signal("BTC-USD", candles)
