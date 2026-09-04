from atlas.trading.indicators import (
    calculate_adx,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
)


def test_rsi_returns_neutral_for_insufficient_data():

    closes = [100, 101, 102]

    result = calculate_rsi(
        closes,
        period=14,
    )

    assert result == [50.0, 50.0, 50.0]


def test_rsi_detects_strong_uptrend():

    closes = [
        100,
        101,
        102,
        103,
        104,
        105,
        106,
        107,
        108,
        109,
        110,
        111,
        112,
        113,
        114,
        115,
    ]

    result = calculate_rsi(
        closes,
        period=14,
    )

    assert result[-1] == 100.0


def test_sma_calculates_simple_moving_average():

    from atlas.trading.indicators import calculate_sma

    closes = [
        10,
        20,
        30,
        40,
        50,
    ]

    result = calculate_sma(
        closes,
        period=3,
    )

    assert result == [
        None,
        None,
        20.0,
        30.0,
        40.0,
    ]


def test_sma_uses_only_previous_available_data():

    from atlas.trading.indicators import calculate_sma

    closes = [
        100,
        110,
        120,
    ]

    result = calculate_sma(
        closes,
        period=2,
    )

    assert result == [
        None,
        105.0,
        115.0,
    ]


def test_ema_uses_sma_seed():
    result = calculate_ema([1.0, 2.0, 3.0, 4.0], period=3)
    assert result[:2] == [None, None]
    assert result[-1] == 3.0


def test_macd_is_positive_in_sustained_uptrend():
    closes = [float(value) for value in range(1, 70)]
    line, signal, histogram = calculate_macd(closes)
    assert line[-1] is not None
    assert signal[-1] is not None
    assert histogram[-1] is not None
    assert line[-1] > 0
    assert histogram[-1] > 0


def test_adx_confirms_directional_uptrend():
    highs = [101.0 + index for index in range(40)]
    lows = [99.0 + index for index in range(40)]
    closes = [100.0 + index for index in range(40)]
    adx, plus_di, minus_di = calculate_adx(highs, lows, closes)
    assert adx[-1] is not None
    assert plus_di[-1] is not None
    assert minus_di[-1] is not None
    assert adx[-1] > 0
    assert plus_di[-1] > minus_di[-1]


def test_adx_rejects_mismatched_series():
    try:
        calculate_adx([1.0], [1.0, 2.0], [1.0])
    except ValueError as exc:
        assert "equal length" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
