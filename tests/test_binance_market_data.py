from atlas.adapters.binance_market_data import BinanceMarketData


class FakeBinance:
    def __init__(self, klines):
        self.klines = klines
        self.calls = []

    def get_klines(self, **kwargs):
        self.calls.append(kwargs)
        return self.klines


def test_binance_klines_become_market_snapshot():
    adapter = FakeBinance([
        [1710000000000, "100", "105", "99", "103", "12.5"],
        [1710000060000, "103", "108", "102", "107", "18.0"],
    ])

    snapshot = BinanceMarketData(adapter).snapshot(
        symbol="BTCUSDT",
        interval="1m",
        limit=2,
    )

    assert snapshot.symbol == "BTCUSDT"
    assert snapshot.price == 107.0
    assert snapshot.timestamp == 1710000060.0
    assert len(snapshot.candles) == 2
    assert snapshot.candles[-1].open == 103.0
    assert snapshot.candles[-1].high == 108.0
    assert snapshot.candles[-1].low == 102.0
    assert snapshot.candles[-1].close == 107.0
    assert snapshot.candles[-1].volume == 18.0
    assert adapter.calls == [{
        "symbol": "BTCUSDT",
        "interval": "1m",
        "limit": 2,
    }]


def test_binance_market_data_rejects_short_kline():
    adapter = FakeBinance([[1710000000000, "100", "105"]])

    try:
        BinanceMarketData(adapter).snapshot("BTCUSDT")
    except ValueError as exc:
        assert "at least 6 fields" in str(exc)
    else:
        raise AssertionError("expected ValueError")
