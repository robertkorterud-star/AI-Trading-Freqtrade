from atlas.trading.trend_following import (
    TrendFollowingAnalyzer,
)


def test_bullish_trend():

    closes = list(
        range(1, 41)
    )

    result = TrendFollowingAnalyzer(
        fast_period=10,
        slow_period=30,
    ).analyze(closes)

    assert result.signal == "BULLISH"
    assert result.fast_average is not None
    assert result.slow_average is not None
    assert result.fast_average > result.slow_average
    assert result.trend_strength > 0
    assert result.data_quality == "GOOD"


def test_bearish_trend():

    closes = list(
        range(100, 60, -1)
    )

    result = TrendFollowingAnalyzer(
        fast_period=10,
        slow_period=30,
    ).analyze(closes)

    assert result.signal == "BEARISH"
    assert result.fast_average < result.slow_average
    assert result.trend_strength < 0


def test_neutral_constant_market():

    closes = [100.0] * 40

    result = TrendFollowingAnalyzer(
        fast_period=10,
        slow_period=30,
    ).analyze(closes)

    assert result.signal == "NEUTRAL"
    assert result.trend_strength == 0.0


def test_partial_data_is_safe():

    result = TrendFollowingAnalyzer(
        fast_period=10,
        slow_period=30,
    ).analyze(
        list(range(1, 21))
    )

    assert result.signal == "UNKNOWN"
    assert result.fast_average is not None
    assert result.slow_average is None
    assert result.data_quality == "PARTIAL"


def test_missing_data_is_safe():

    result = TrendFollowingAnalyzer().analyze([])

    assert result.signal == "UNKNOWN"
    assert result.fast_average is None
    assert result.slow_average is None
    assert result.trend_strength == 0.0
    assert result.data_quality == "MISSING"


def test_invalid_periods_are_rejected():

    try:
        TrendFollowingAnalyzer(
            fast_period=30,
            slow_period=10,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected ValueError."
        )


def test_trend_following_does_not_create_trade_decision():

    result = TrendFollowingAnalyzer().analyze(
        list(range(1, 41))
    )

    assert not hasattr(result, "buy")
    assert not hasattr(result, "sell")
    assert not hasattr(result, "decision")
    assert not hasattr(result, "action")
