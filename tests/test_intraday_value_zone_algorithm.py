import pytest

from atlas.algorithms.base import AlgorithmSignal
from atlas.algorithms.value_zone import IntradayValueZoneAlgorithm
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


def test_value_zone_returns_structured_signal():
    algorithm = IntradayValueZoneAlgorithm()

    closes = [100.0] * 24 + [
        99.0,
        98.0,
        98.5,
    ]

    signal = algorithm.generate_signal(
        "BTC-USD",
        candles_from_closes(closes),
    )

    assert isinstance(signal, AlgorithmSignal)
    assert signal.algorithm == "intraday_value_zone"
    assert signal.symbol == "BTC-USD"
    assert signal.timeframe == "5m"
    assert signal.expected_edge is None
    assert 0.0 <= signal.score <= 100.0
    assert 50.0 <= signal.confidence <= 90.0
    assert signal.reasoning


def test_value_zone_can_identify_buy_after_low_and_reversal():
    algorithm = IntradayValueZoneAlgorithm(
        range_window=24,
        mean_window=12,
        momentum_window=3,
        deviation_threshold_percent=0.50,
        reversal_threshold_percent=0.05,
    )

    closes = (
        [100.0] * 21
        + [95.0, 96.0, 97.0]
    )

    signal = algorithm.generate_signal(
        "BTC-USD",
        candles_from_closes(closes),
    )

    assert signal.action is Action.BUY


def test_value_zone_can_identify_sell_after_high_and_reversal():
    algorithm = IntradayValueZoneAlgorithm(
        range_window=24,
        mean_window=12,
        momentum_window=3,
        deviation_threshold_percent=0.50,
        reversal_threshold_percent=0.05,
    )

    closes = (
        [100.0] * 21
        + [105.0, 104.0, 103.0]
    )

    signal = algorithm.generate_signal(
        "BTC-USD",
        candles_from_closes(closes),
    )

    assert signal.action is Action.SELL


def test_value_zone_holds_without_reversal_confirmation():
    algorithm = IntradayValueZoneAlgorithm(
        range_window=24,
        mean_window=12,
        momentum_window=3,
    )

    closes = [100.0] * 24 + [
        98.0,
        97.0,
        96.0,
    ]

    signal = algorithm.generate_signal(
        "BTC-USD",
        candles_from_closes(closes),
    )

    assert signal.action is Action.HOLD


def test_value_zone_holds_near_middle_of_range():
    algorithm = IntradayValueZoneAlgorithm()

    closes = (
        [100.0] * 12
        + [98.0, 99.0, 100.0, 101.0, 100.0, 99.0]
        + [100.0] * 6
    )

    signal = algorithm.generate_signal(
        "BTC-USD",
        candles_from_closes(closes),
    )

    assert signal.action is Action.HOLD


def test_value_zone_requires_enough_candles():
    algorithm = IntradayValueZoneAlgorithm(
        range_window=24,
    )

    with pytest.raises(
        ValueError,
        match="at least 24 candles",
    ):
        algorithm.generate_signal(
            "BTC-USD",
            candles_from_closes([100.0] * 23),
        )


def test_value_zone_rejects_invalid_close():
    algorithm = IntradayValueZoneAlgorithm()

    candles = candles_from_closes(
        [100.0] * 23 + [0.0]
    )

    with pytest.raises(
        ValueError,
        match="finite positive close prices",
    ):
        algorithm.generate_signal(
            "BTC-USD",
            candles,
        )


def test_value_zone_thresholds_are_configurable():
    algorithm = IntradayValueZoneAlgorithm(
        buy_zone=0.20,
        sell_zone=0.80,
        deviation_threshold_percent=2.0,
    )

    assert algorithm.buy_zone == 0.20
    assert algorithm.sell_zone == 0.80
    assert algorithm.deviation_threshold_percent == 2.0
