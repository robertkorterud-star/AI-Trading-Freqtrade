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


def test_market_snapshot_rejects_non_chronological_base_candles():
    candles = (
        _candle(2, 101),
        _candle(1, 100),
    )

    try:
        MarketSnapshot.from_candles(
            symbol="NVDA",
            candles=candles,
        )
    except ValueError as error:
        assert "strictly increasing" in str(error)
    else:
        raise AssertionError(
            "Expected non-chronological base candles to be rejected."
        )


def test_market_snapshot_rejects_duplicate_timeframe_timestamps():
    candles = (
        _candle(1, 100),
        _candle(2, 101),
    )
    hourly = (
        _candle(3, 102),
        _candle(3, 103),
    )

    try:
        MarketSnapshot.from_candles(
            symbol="NVDA",
            candles=candles,
            timeframe_candles={"1h": hourly},
        )
    except ValueError as error:
        assert "strictly increasing" in str(error)
    else:
        raise AssertionError(
            "Expected duplicate timeframe timestamps to be rejected."
        )


def test_market_snapshot_rejects_timestamp_older_than_latest_candle():
    candles = (
        _candle(100, 100),
        _candle(200, 101),
    )

    try:
        MarketSnapshot(
            symbol="BTC-USD",
            timestamp=150,
            price=101,
            candles=candles,
        )
    except ValueError as error:
        assert "latest candle" in str(error)
    else:
        raise AssertionError(
            "Expected a stale snapshot timestamp to be rejected."
        )
