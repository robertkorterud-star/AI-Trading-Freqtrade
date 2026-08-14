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
