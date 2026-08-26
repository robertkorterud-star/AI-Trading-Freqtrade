from atlas.trading.indicator_engine import (
    IndicatorEngine,
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
                "volume": 1000 + index,
            }
        )

    return result


def test_indicator_engine_calculates_core_features():
    result = IndicatorEngine().calculate(
        _candles()
    )

    assert result.close > 0

    assert result.sma20 is not None
    assert result.sma50 is not None
    assert result.sma200 is not None

    assert result.ema20 is not None
    assert result.ema50 is not None

    assert result.rsi14 is not None

    assert result.atr14 is not None
    assert result.atr_percent is not None

    assert result.bollinger_middle is not None
    assert result.bollinger_upper is not None
    assert result.bollinger_lower is not None

    assert result.obv is not None
    assert result.relative_volume is not None

    assert result.data_quality == "GOOD"


def test_indicator_engine_detects_uptrend():
    result = IndicatorEngine().calculate(
        _candles(
            start=100,
            step=1.0,
            count=250,
        )
    )

    assert result.ema20 > result.ema50
    assert result.sma20 > result.sma50
    assert result.rsi14 > 50


def test_indicator_engine_handles_missing_data():
    result = IndicatorEngine().calculate([])

    assert result.data_quality == "MISSING"
    assert result.close == 0.0
    assert result.sma20 is None
    assert result.rsi14 is None
    assert result.atr14 is None
    assert result.relative_volume is None


def test_indicator_engine_reports_poor_data():
    result = IndicatorEngine().calculate(
        _candles(count=20)
    )

    assert result.data_quality == "POOR"
    assert result.sma20 is not None or result.sma20 is None
    assert result.sma50 is None
    assert result.sma200 is None


def test_indicator_engine_breakout_detection():
    candles = _candles(
        start=100,
        step=0.1,
        count=100,
    )

    candles[-1]["close"] = 200.0
    candles[-1]["high"] = 200.2

    result = IndicatorEngine().calculate(
        candles
    )

    assert result.breakout20 is True
    assert result.breakout50 is True
