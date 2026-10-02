import pytest

from atlas.algorithms import IntradayTrendAlgorithm
from atlas.models.action import Action


def candles(values):
    return [
        {
            "timestamp": index,
            "open": value,
            "high": value,
            "low": value,
            "close": value,
            "volume": 1000,
        }
        for index, value in enumerate(values)
    ]


def test_trend_algorithm_is_exported():
    algorithm = IntradayTrendAlgorithm()

    assert algorithm.name == "intraday_trend"
    assert algorithm.timeframe == "5m"


def test_trend_algorithm_generates_buy_signal():
    algorithm = IntradayTrendAlgorithm(
        short_window=3,
        long_window=6,
        signal_threshold_percent=0.20,
    )

    result = algorithm.generate_signal(
        "BTC-USD",
        candles([100, 100, 100, 100, 101, 102, 104]),
    )

    assert result.action is Action.BUY
    assert result.algorithm == "intraday_trend"
    assert result.symbol == "BTC-USD"
    assert 0.0 <= result.score <= 100.0
    assert 0.0 <= result.confidence <= 100.0
    assert result.reasoning


def test_trend_algorithm_generates_sell_signal():
    algorithm = IntradayTrendAlgorithm(
        short_window=3,
        long_window=6,
        signal_threshold_percent=0.20,
    )

    result = algorithm.generate_signal(
        "BTC-USD",
        candles([104, 102, 101, 100, 100, 100, 100]),
    )

    assert result.action is Action.SELL
    assert result.score < 50.0


def test_trend_algorithm_can_hold():
    algorithm = IntradayTrendAlgorithm(
        short_window=3,
        long_window=6,
        signal_threshold_percent=0.20,
    )

    result = algorithm.generate_signal(
        "BTC-USD",
        candles([100, 100, 100, 100, 100.02, 100.01, 100]),
    )

    assert result.action is Action.HOLD
    assert result.score == 50.0


def test_trend_algorithm_rejects_insufficient_candles():
    algorithm = IntradayTrendAlgorithm(
        short_window=3,
        long_window=6,
    )

    with pytest.raises(ValueError, match="at least 7 candles"):
        algorithm.generate_signal(
            "BTC-USD",
            candles([100, 101, 102]),
        )


def test_trend_algorithm_rejects_invalid_prices():
    algorithm = IntradayTrendAlgorithm()

    with pytest.raises(ValueError, match="finite positive"):
        algorithm.generate_signal(
            "BTC-USD",
            candles([100] * 12 + [0]),
        )
