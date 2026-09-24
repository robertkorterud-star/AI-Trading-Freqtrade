from atlas.trading.market_data import Candle, MarketSnapshot


def _candle(timestamp, close):
    return Candle(
        timestamp=float(timestamp),
        open=float(close - 1),
        high=float(close + 1),
        low=float(close - 1),
        close=float(close),
        volume=100.0,
    )


def test_market_snapshot_preserves_multiple_timeframes():
    daily = (_candle(1, 100), _candle(2, 101))
    hourly = (_candle(3, 102), _candle(4, 103))

    snapshot = MarketSnapshot.from_candles(
        symbol="NVDA",
        candles=daily,
        timeframe_candles={
            "1h": hourly,
            "1d": daily,
        },
    )

    assert snapshot.symbol == "NVDA"
    assert snapshot.price == 101.0
    assert snapshot.candles == daily
    assert snapshot.timeframe_candles["1h"] == hourly
    assert snapshot.timeframe_candles["1d"] == daily


def test_market_snapshot_normalizes_timeframe_candles_to_tuples():
    daily = [_candle(1, 100), _candle(2, 101)]
    hourly = [_candle(3, 102)]

    snapshot = MarketSnapshot.from_candles(
        symbol="NVDA",
        candles=daily,
        timeframe_candles={"1h": hourly},
    )

    assert isinstance(snapshot.candles, tuple)
    assert isinstance(snapshot.timeframe_candles["1h"], tuple)


def test_market_snapshot_rejects_empty_timeframe_candles():
    candles = (_candle(1, 100),)

    try:
        MarketSnapshot.from_candles(
            symbol="NVDA",
            candles=candles,
            timeframe_candles={"1h": []},
        )
    except ValueError as error:
        assert "timeframe candles must not be empty" in str(error)
    else:
        raise AssertionError(
            "Expected empty timeframe candles to be rejected."
        )
