import pytest

from atlas.algorithms.base import AlgorithmSignal
from atlas.algorithms.mean_reversion import (
    IntradayMeanReversionAlgorithm,
)
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


def test_mean_reversion_returns_structured_buy_signal():
    algorithm = IntradayMeanReversionAlgorithm()

    candles = candles_from_closes(
        [
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            97.0,
        ]
    )

    signal = algorithm.generate_signal(
        "BTC-USD",
        candles,
    )

    assert isinstance(signal, AlgorithmSignal)
    assert signal.algorithm == "intraday_mean_reversion"
    assert signal.symbol == "BTC-USD"
    assert signal.timeframe == "5m"
    assert signal.action is Action.BUY
    assert signal.expected_edge is None
    assert 50.0 <= signal.score <= 100.0
    assert 50.0 <= signal.confidence <= 90.0
    assert signal.reasoning


def test_mean_reversion_returns_sell_signal():
    algorithm = IntradayMeanReversionAlgorithm()

    candles = candles_from_closes(
        [
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            103.0,
        ]
    )

    signal = algorithm.generate_signal(
        "BTC-USD",
        candles,
    )

    assert signal.action is Action.SELL


def test_mean_reversion_returns_hold_near_mean():
    algorithm = IntradayMeanReversionAlgorithm()

    candles = candles_from_closes(
        [
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.5,
        ]
    )

    signal = algorithm.generate_signal(
        "BTC-USD",
        candles,
    )

    assert signal.action is Action.HOLD


def test_mean_reversion_requires_enough_candles():
    algorithm = IntradayMeanReversionAlgorithm()

    with pytest.raises(
        ValueError,
        match="at least 13 candles",
    ):
        algorithm.generate_signal(
            "BTC-USD",
            candles_from_closes([100.0] * 12),
        )


def test_mean_reversion_rejects_invalid_close_prices():
    algorithm = IntradayMeanReversionAlgorithm()

    candles = candles_from_closes(
        [100.0] * 12 + [0.0]
    )

    with pytest.raises(
        ValueError,
        match="finite positive close prices",
    ):
        algorithm.generate_signal(
            "BTC-USD",
            candles,
        )


def test_mean_reversion_threshold_can_be_configured():
    algorithm = IntradayMeanReversionAlgorithm(
        deviation_threshold_percent=2.0,
    )

    candles = candles_from_closes(
        [
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            101.0,
        ]
    )

    signal = algorithm.generate_signal(
        "BTC-USD",
        candles,
    )

    assert signal.action is Action.HOLD
