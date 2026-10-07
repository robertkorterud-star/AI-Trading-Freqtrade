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


def test_binance_historical_provider_paginates_date_range():
    class PaginatedBinance:
        def __init__(self):
            self.calls = []

        def get_klines(self, **kwargs):
            self.calls.append(kwargs)

            if len(self.calls) == 1:
                return [
                    [
                        1767225600000,
                        "100",
                        "105",
                        "99",
                        "103",
                        "12.5",
                        1767239999999,
                    ],
                    [
                        1767240000000,
                        "103",
                        "108",
                        "102",
                        "107",
                        "18.0",
                        1767254399999,
                    ],
                ]

            if len(self.calls) == 2:
                return [
                    [
                        1767254400000,
                        "107",
                        "110",
                        "106",
                        "109",
                        "20.0",
                        1767268799999,
                    ],
                ]

            return []

    adapter = PaginatedBinance()

    provider = BinanceHistoricalDataProvider(
        adapter=adapter,
        interval="4h",
        limit=2,
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

    result = provider.load(
        "BTCUSDT",
        start=start,
        end=end,
    )

    assert len(result.bars) == 3
    assert [
        bar.timestamp
        for bar in result.bars
    ] == [
        datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 4, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc),
    ]

    assert len(adapter.calls) == 2

    assert adapter.calls[0] == {
        "symbol": "BTCUSDT",
        "interval": "4h",
        "limit": 2,
        "start_time": 1767225600000,
        "end_time": 1767312000000,
    }

    # Continue immediately after the final close time from page one.
    assert adapter.calls[1] == {
        "symbol": "BTCUSDT",
        "interval": "4h",
        "limit": 2,
        "start_time": 1767254400000,
        "end_time": 1767312000000,
    }


def test_binance_historical_provider_stops_when_pagination_makes_no_progress():
    repeated_page = [
        [
            1767225600000,
            "100",
            "105",
            "99",
            "103",
            "12.5",
            1767239999999,
        ],
        [
            1767240000000,
            "103",
            "108",
            "102",
            "107",
            "18.0",
            1767254399999,
        ],
    ]

    class RepeatingBinance:
        def __init__(self):
            self.calls = []

        def get_klines(self, **kwargs):
            self.calls.append(kwargs)

            # First page is valid. The second response repeats the same
            # full page instead of advancing through history.
            if len(self.calls) <= 2:
                return repeated_page

            raise AssertionError(
                "pagination continued after Binance stopped making progress"
            )

    adapter = RepeatingBinance()

    provider = BinanceHistoricalDataProvider(
        adapter=adapter,
        interval="4h",
        limit=2,
        now=lambda: datetime(
            2026, 1, 10, tzinfo=timezone.utc
        ),
    )

    result = provider.load(
        "BTCUSDT",
        start=datetime(
            2026, 1, 1, tzinfo=timezone.utc
        ),
        end=datetime(
            2026, 1, 3, tzinfo=timezone.utc
        ),
    )

    assert len(adapter.calls) == 2

    assert [
        bar.timestamp
        for bar in result.bars
    ] == [
        datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 4, 0, tzinfo=timezone.utc),
    ]


def test_binance_historical_provider_can_label_injected_market_source():
    adapter = FakeBinance([
        [
            1767225600000,
            "100",
            "105",
            "99",
            "103",
            "12.5",
            1767225899999,
        ],
    ])

    provider = BinanceHistoricalDataProvider(
        adapter=adapter,
        interval="5m",
        source="binance_futures",
        now=lambda: datetime(
            2026, 1, 2, tzinfo=timezone.utc
        ),
    )

    result = provider.load("BTCUSDT")

    assert result.symbol == "BTCUSDT"
    assert result.timeframe == "5m"
    assert result.source == "binance_futures"
    assert len(result.bars) == 1


def test_binance_historical_provider_loads_paginated_raw_klines():
    class PaginatedBinance:
        def __init__(self):
            self.calls = []

        def get_klines(self, **kwargs):
            self.calls.append(kwargs)

            if len(self.calls) == 1:
                return [
                    [
                        1767225600000,
                        "100",
                        "105",
                        "99",
                        "103",
                        "12.5",
                        1767225899999,
                        "0",
                        10,
                        "7.5",
                        "0",
                        "0",
                    ],
                    [
                        1767225900000,
                        "103",
                        "108",
                        "102",
                        "107",
                        "18.0",
                        1767226199999,
                        "0",
                        12,
                        "10.8",
                        "0",
                        "0",
                    ],
                ]

            if len(self.calls) == 2:
                return [
                    [
                        1767226200000,
                        "107",
                        "110",
                        "106",
                        "109",
                        "20.0",
                        1767226499999,
                        "0",
                        15,
                        "13.0",
                        "0",
                        "0",
                    ],
                ]

            return []

    adapter = PaginatedBinance()
    provider = BinanceHistoricalDataProvider(
        adapter=adapter,
        interval="5m",
        limit=2,
        now=lambda: datetime(
            2026, 1, 10, tzinfo=timezone.utc
        ),
    )

    result = provider.load_raw_klines(
        "BTCUSDT",
        start=datetime(
            2026, 1, 1, 0, 0, tzinfo=timezone.utc
        ),
        end=datetime(
            2026, 1, 1, 1, 0, tzinfo=timezone.utc
        ),
    )

    assert len(result) == 3

    # Preserve Binance raw taker-buy base volume.
    assert result[0][9] == "7.5"
    assert result[1][9] == "10.8"
    assert result[2][9] == "13.0"

    assert len(adapter.calls) == 2
    assert adapter.calls[1]["start_time"] == 1767226200000
