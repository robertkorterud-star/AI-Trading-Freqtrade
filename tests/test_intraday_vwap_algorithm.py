import pytest

from atlas.algorithms.base import AlgorithmSignal
from atlas.algorithms.vwap import IntradayVWAPAlgorithm
from atlas.models.action import Action


def candles_from_closes(
    closes,
    volumes=None,
):
    if volumes is None:
        volumes = [1.0] * len(closes)

    return [
        {
            "timestamp": str(index),
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": volume,
        }
        for index, (close, volume) in enumerate(
            zip(closes, volumes)
        )
    ]


def test_vwap_returns_structured_signal_for_bullish_alignment():
    algorithm = IntradayVWAPAlgorithm(
        window=20,
        momentum_window=3,
    )

    closes = [100.0] * 20 + [
        100.2,
        100.4,
        101.0,
    ]

    signal = algorithm.generate_signal(
        "BTC-USD",
        candles_from_closes(closes),
    )

    assert isinstance(signal, AlgorithmSignal)
    assert signal.algorithm == "intraday_vwap"
    assert signal.symbol == "BTC-USD"
    assert signal.timeframe == "5m"
    assert signal.action is Action.BUY
    assert 50.0 <= signal.score <= 100.0
    assert 50.0 <= signal.confidence <= 90.0
    assert signal.expected_edge is None
    assert signal.reasoning


def test_vwap_returns_structured_signal_for_bearish_alignment():
    algorithm = IntradayVWAPAlgorithm(
        window=20,
        momentum_window=3,
    )

    closes = [100.0] * 20 + [
        99.8,
        99.6,
        99.0,
    ]

    signal = algorithm.generate_signal(
        "BTC-USD",
        candles_from_closes(closes),
    )

    assert signal.action is Action.SELL


def test_vwap_returns_hold_without_confirmation():
    algorithm = IntradayVWAPAlgorithm(
        window=20,
        momentum_window=3,
        deviation_threshold_percent=0.50,
        momentum_threshold_percent=0.50,
    )

    closes = [100.0] * 20 + [
        100.1,
        100.2,
        100.3,
    ]

    signal = algorithm.generate_signal(
        "BTC-USD",
        candles_from_closes(closes),
    )

    assert signal.action is Action.HOLD
    assert signal.score == 50.0


def test_vwap_uses_volume_weighting():
    algorithm = IntradayVWAPAlgorithm(
        window=20,
        momentum_window=3,
    )

    closes = [100.0] * 22 + [
        101.0,
    ]

    volumes = [1.0] * 22 + [
        100.0,
    ]

    signal = algorithm.generate_signal(
        "BTC-USD",
        candles_from_closes(
            closes,
            volumes,
        ),
    )

    assert signal.action is Action.BUY


def test_vwap_requires_enough_candles():
    algorithm = IntradayVWAPAlgorithm(
        window=20,
        momentum_window=3,
    )

    with pytest.raises(
        ValueError,
        match="at least 23 candles",
    ):
        algorithm.generate_signal(
            "BTC-USD",
            candles_from_closes([100.0] * 22),
        )


def test_vwap_rejects_invalid_prices():
    algorithm = IntradayVWAPAlgorithm(
        window=20,
        momentum_window=3,
    )

    candles = candles_from_closes(
        [100.0] * 22 + [0.0]
    )

    with pytest.raises(
        ValueError,
        match="positive OHLC prices",
    ):
        algorithm.generate_signal(
            "BTC-USD",
            candles,
        )


def test_vwap_rejects_negative_volume():
    algorithm = IntradayVWAPAlgorithm(
        window=20,
        momentum_window=3,
    )

    candles = candles_from_closes(
        [100.0] * 23,
        [1.0] * 22 + [-1.0],
    )

    with pytest.raises(
        ValueError,
        match="non-negative volume",
    ):
        algorithm.generate_signal(
            "BTC-USD",
            candles,
        )


def test_vwap_rejects_zero_total_volume():
    algorithm = IntradayVWAPAlgorithm(
        window=20,
        momentum_window=3,
    )

    candles = candles_from_closes(
        [100.0] * 23,
        [0.0] * 23,
    )

    with pytest.raises(
        ValueError,
        match="positive total volume",
    ):
        algorithm.generate_signal(
            "BTC-USD",
            candles,
        )
