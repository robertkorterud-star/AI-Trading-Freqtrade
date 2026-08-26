from dataclasses import replace

from atlas.trading.indicator_engine import (
    IndicatorEngine,
)
from atlas.trading.market_regime import (
    MarketRegimeAnalyzer,
)


def _candles(
    start=100.0,
    step=0.5,
    count=250,
):
    result = []

    for index in range(count):
        close = start + index * step

        result.append(
            {
                "timestamp": str(index),
                "open": close - 0.1,
                "high": close + 0.2,
                "low": close - 0.2,
                "close": close,
                "volume": 1000,
            }
        )

    return result


def test_market_regime_detects_bullish_trend():
    indicators = IndicatorEngine().calculate(
        _candles(
            start=100,
            step=1.0,
        )
    )

    regime = MarketRegimeAnalyzer().analyze(
        indicators
    )

    assert regime.regime == "BREAKOUT_UP"
    assert regime.confidence > 0
    assert regime.trend_strength >= 0


def test_market_regime_detects_missing_data():
    indicators = IndicatorEngine().calculate([])

    regime = MarketRegimeAnalyzer().analyze(
        indicators
    )

    assert regime.regime == "UNKNOWN"
    assert regime.confidence == 0.0
    assert regime.volatility_level == "UNKNOWN"


def test_market_regime_detects_high_volatility():
    indicators = IndicatorEngine().calculate(
        _candles(
            start=100,
            step=0.5,
        )
    )

    indicators = replace(
        indicators,
        atr_percent=5.0,
        bollinger_width=12.0,
        adx14=10.0,
        ema20=100.0,
        ema50=100.0,
    )

    regime = MarketRegimeAnalyzer().analyze(
        indicators
    )

    assert regime.regime == "HIGH_VOLATILITY"
    assert regime.volatility_level == "HIGH"


def test_market_regime_detects_low_volatility():
    indicators = IndicatorEngine().calculate(
        _candles(
            start=100,
            step=0.01,
        )
    )

    indicators = replace(
        indicators,
        atr_percent=0.5,
        bollinger_width=2.0,
        adx14=10.0,
        ema20=100.0,
        ema50=100.0,
    )

    regime = MarketRegimeAnalyzer().analyze(
        indicators
    )

    assert regime.regime == "LOW_VOLATILITY"
    assert regime.volatility_level == "LOW"


def test_market_regime_does_not_trade():
    indicators = IndicatorEngine().calculate(
        _candles()
    )

    regime = MarketRegimeAnalyzer().analyze(
        indicators
    )

    assert regime.regime not in {
        "BUY",
        "SELL",
    }
