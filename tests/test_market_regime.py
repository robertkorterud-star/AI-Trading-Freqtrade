import pytest

from atlas.algorithms.regime import (
    MarketRegime,
    MarketRegimeEngine,
    MarketRegimeResult,
)


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


def test_bull_trend_is_detected():
    engine = MarketRegimeEngine(
        trend_window=5,
        volatility_window=5,
    )

    closes = [100.0] * 5 + [
        101.0,
        102.0,
        103.0,
        104.0,
        106.0,
    ]

    result = engine.analyze(
        "BTC-USD",
        candles_from_closes(closes),
    )

    assert isinstance(result, MarketRegimeResult)
    assert result.regime is MarketRegime.BULL_TREND
    assert result.trend_score == pytest.approx(6.0)
    assert result.symbol == "BTC-USD"
    assert result.timeframe == "1h"


def test_bear_trend_is_detected():
    engine = MarketRegimeEngine(
        trend_window=5,
        volatility_window=5,
    )

    closes = [100.0] * 5 + [
        99.0,
        98.0,
        97.0,
        96.0,
        94.0,
    ]

    result = engine.analyze(
        "BTC-USD",
        candles_from_closes(closes),
    )

    assert result.regime is MarketRegime.BEAR_TREND
    assert result.trend_score == pytest.approx(-6.0)


def test_sideways_market_is_detected():
    engine = MarketRegimeEngine(
        trend_window=5,
        volatility_window=5,
    )

    closes = [
        100.0,
        100.2,
        99.9,
        100.1,
        100.0,
        100.1,
    ]

    result = engine.analyze(
        "BTC-USD",
        candles_from_closes(closes),
    )

    assert result.regime is MarketRegime.SIDEWAYS


def test_high_volatility_takes_priority():
    engine = MarketRegimeEngine(
        trend_window=5,
        volatility_window=5,
        high_volatility_threshold=4.0,
    )

    closes = [
        100.0,
        110.0,
        100.0,
        110.0,
        100.0,
        110.0,
    ]

    result = engine.analyze(
        "BTC-USD",
        candles_from_closes(closes),
    )

    assert result.regime is MarketRegime.HIGH_VOLATILITY
    assert result.volatility_percent > 4.0


def test_insufficient_candles_raise():
    engine = MarketRegimeEngine(
        trend_window=5,
        volatility_window=5,
    )

    with pytest.raises(ValueError, match="at least 6 candles"):
        engine.analyze(
            "BTC-USD",
            candles_from_closes([100.0] * 5),
        )


def test_invalid_close_prices_raise():
    engine = MarketRegimeEngine()

    closes = [100.0] * 20 + [0.0]

    with pytest.raises(
        ValueError,
        match="finite positive close prices",
    ):
        engine.analyze(
            "BTC-USD",
            candles_from_closes(closes),
        )


def test_invalid_configuration_raises():
    with pytest.raises(ValueError):
        MarketRegimeEngine(trend_window=1)

    with pytest.raises(ValueError):
        MarketRegimeEngine(volatility_window=1)

    with pytest.raises(ValueError):
        MarketRegimeEngine(bull_threshold=0)

    with pytest.raises(ValueError):
        MarketRegimeEngine(bear_threshold=0)

    with pytest.raises(ValueError):
        MarketRegimeEngine(
            high_volatility_threshold=0
        )


def test_regime_confidence_is_bounded():
    engine = MarketRegimeEngine(
        trend_window=5,
        volatility_window=5,
    )

    closes = [100.0] * 5 + [
        120.0,
        130.0,
        140.0,
        150.0,
        160.0,
    ]

    result = engine.analyze(
        "BTC-USD",
        candles_from_closes(closes),
    )

    assert 50.0 <= result.confidence <= 90.0
