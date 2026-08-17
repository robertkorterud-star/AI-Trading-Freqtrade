from atlas.trading.indicators import calculate_rsi


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
