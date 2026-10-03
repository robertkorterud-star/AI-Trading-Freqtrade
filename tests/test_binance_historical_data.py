from datetime import datetime, timezone

from atlas.adapters.binance_historical_data import (
    BinanceHistoricalDataProvider,
)


class FakeBinance:
    def __init__(self, klines):
        self.klines = klines
        self.calls = []

    def get_klines(self, **kwargs):
        self.calls.append(kwargs)
        return self.klines


def test_binance_historical_provider_returns_only_closed_ohlcv_bars():
    adapter = FakeBinance([
        [
            1767225600000,       # open time
            "100",
            "105",
            "99",
            "103",
            "12.5",
            1767239999999,       # close time - closed
        ],
        [
            1767240000000,
            "103",
            "108",
            "102",
            "107",
            "18.0",
            1767254399999,       # close time - still open
        ],
    ])

    provider = BinanceHistoricalDataProvider(
        adapter=adapter,
        interval="4h",
        limit=500,
        now=lambda: datetime(
            2026, 1, 1, 6, 0, tzinfo=timezone.utc
        ),
    )

    result = provider.load("BTCUSDT")

    assert result.symbol == "BTCUSDT"
    assert result.timeframe == "4h"
    assert result.source == "binance"
    assert len(result.bars) == 1

    bar = result.bars[0]

    assert bar.timestamp == datetime(
        2026, 1, 1, 0, 0, tzinfo=timezone.utc
    )
    assert bar.open == 100.0
    assert bar.high == 105.0
    assert bar.low == 99.0
    assert bar.close == 103.0
    assert bar.volume == 12.5

    assert adapter.calls == [{
        "symbol": "BTCUSDT",
        "interval": "4h",
        "limit": 500,
        "start_time": None,
        "end_time": None,
    }]


def test_binance_historical_provider_maps_date_range_to_milliseconds():
    adapter = FakeBinance([])

    provider = BinanceHistoricalDataProvider(
        adapter=adapter,
        interval="4h",
        now=lambda: datetime(
            2026, 1, 10, tzinfo=timezone.utc
        ),
    )

    start = datetime(
        2026, 1, 1, tzinfo=timezone.utc
    )
    end = datetime(
        2026, 1, 2, tzinfo=timezone.utc
    )

    provider.load(
        "ETHUSDT",
        start=start,
        end=end,
    )

    assert adapter.calls == [{
        "symbol": "ETHUSDT",
        "interval": "4h",
        "limit": 500,
        "start_time": 1767225600000,
        "end_time": 1767312000000,
    }]
