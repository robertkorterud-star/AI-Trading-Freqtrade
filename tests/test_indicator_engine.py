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


def test_indicator_engine_confirms_swing_high_without_lookahead():
    candles = [
        {"open": 99, "high": 100, "low": 98, "close": 99, "volume": 1000},
        {"open": 100, "high": 102, "low": 99, "close": 101, "volume": 1000},
        {"open": 101, "high": 105, "low": 100, "close": 104, "volume": 1000},
        {"open": 103, "high": 103, "low": 100, "close": 101, "volume": 1000},
        {"open": 101, "high": 102, "low": 99, "close": 100, "volume": 1000},
    ]

    before_confirmation = IndicatorEngine().calculate(
        candles[:4]
    )
    confirmed = IndicatorEngine().calculate(
        candles
    )

    assert before_confirmation.swing_high is None
    assert confirmed.swing_high == 105.0


def test_indicator_engine_confirms_swing_low_without_lookahead():
    candles = [
        {"open": 106, "high": 107, "low": 105, "close": 106, "volume": 1000},
        {"open": 105, "high": 106, "low": 103, "close": 104, "volume": 1000},
        {"open": 104, "high": 105, "low": 100, "close": 101, "volume": 1000},
        {"open": 102, "high": 104, "low": 101, "close": 103, "volume": 1000},
        {"open": 103, "high": 105, "low": 102, "close": 104, "volume": 1000},
    ]

    before_confirmation = IndicatorEngine().calculate(
        candles[:4]
    )
    confirmed = IndicatorEngine().calculate(
        candles
    )

    assert before_confirmation.swing_low is None
    assert confirmed.swing_low == 100.0


def test_indicator_engine_preserves_confirmed_swing_order():
    candles = [
        {"open": 99, "high": 100, "low": 98, "close": 99, "volume": 1000},
        {"open": 100, "high": 101, "low": 97, "close": 100, "volume": 1000},
        {"open": 100, "high": 102, "low": 95, "close": 101, "volume": 1000},
        {"open": 102, "high": 104, "low": 98, "close": 103, "volume": 1000},
        {"open": 104, "high": 110, "low": 101, "close": 108, "volume": 1000},
        {"open": 107, "high": 108, "low": 102, "close": 105, "volume": 1000},
        {"open": 105, "high": 106, "low": 101, "close": 103, "volume": 1000},
    ]

    result = IndicatorEngine().calculate(candles)

    assert result.swing_low == 95.0
    assert result.swing_low_index == 2

    assert result.swing_high == 110.0
    assert result.swing_high_index == 4

    assert result.swing_low_index < result.swing_high_index


def test_indicator_engine_calculates_bullish_fibonacci_from_confirmed_swing():
    candles = [
        {"open": 99, "high": 100, "low": 98, "close": 99, "volume": 1000},
        {"open": 100, "high": 101, "low": 97, "close": 100, "volume": 1000},
        {"open": 100, "high": 102, "low": 95, "close": 101, "volume": 1000},
        {"open": 102, "high": 104, "low": 98, "close": 103, "volume": 1000},
        {"open": 104, "high": 110, "low": 101, "close": 108, "volume": 1000},
        {"open": 107, "high": 108, "low": 102, "close": 105, "volume": 1000},
        {"open": 105, "high": 106, "low": 101, "close": 103, "volume": 1000},
    ]

    result = IndicatorEngine().calculate(candles)

    assert result.fib_direction == "bullish"
    assert result.fib_23_6 == 106.46
    assert result.fib_38_2 == 104.27
    assert result.fib_50_0 == 102.5
    assert result.fib_61_8 == 100.73
    assert result.fib_78_6 == 98.21


def test_indicator_engine_calculates_bearish_fibonacci_from_confirmed_swing():
    candles = [
        {"open": 104, "high": 106, "low": 103, "close": 105, "volume": 1000},
        {"open": 105, "high": 108, "low": 102, "close": 107, "volume": 1000},
        {"open": 107, "high": 110, "low": 103, "close": 108, "volume": 1000},
        {"open": 106, "high": 107, "low": 100, "close": 102, "volume": 1000},
        {"open": 101, "high": 105, "low": 95, "close": 97, "volume": 1000},
        {"open": 98, "high": 104, "low": 97, "close": 100, "volume": 1000},
        {"open": 100, "high": 103, "low": 98, "close": 102, "volume": 1000},
    ]

    result = IndicatorEngine().calculate(candles)

    assert result.swing_high == 110.0
    assert result.swing_high_index == 2
    assert result.swing_low == 95.0
    assert result.swing_low_index == 4

    assert result.fib_direction == "bearish"
    assert result.fib_23_6 == 98.54
    assert result.fib_38_2 == 100.73
    assert result.fib_50_0 == 102.5
    assert result.fib_61_8 == 104.27
    assert result.fib_78_6 == 106.79
