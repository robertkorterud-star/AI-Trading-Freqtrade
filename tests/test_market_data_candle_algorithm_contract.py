from atlas.trading.market_data import Candle


def test_candle_exposes_mapping_style_ohlcv_fields():
    candle = Candle(
        timestamp=1.0,
        open=100.0,
        high=105.0,
        low=99.0,
        close=103.0,
        volume=12.0,
    )

    assert candle["open"] == 100.0
    assert candle["high"] == 105.0
    assert candle["low"] == 99.0
    assert candle["close"] == 103.0
    assert candle["volume"] == 12.0
    assert candle.get("close") == 103.0
    assert candle.get("missing") is None
