from datetime import datetime, timedelta, timezone

from atlas.database.connection import Database
from atlas.database.schema import initialize_database
from atlas.database.historical_market_data_repository import (
    HistoricalMarketDataRepository,
)
from atlas.trading.historical_market_data import (
    HistoricalMarketData,
    OHLCVBar,
)
from atlas.trading.repository_historical_data_provider import (
    RepositoryHistoricalDataProvider,
)


def _data():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    return HistoricalMarketData(
        symbol="BTCUSDT",
        timeframe="4h",
        source="binance",
        bars=[
            OHLCVBar(
                timestamp=start + timedelta(hours=4 * index),
                open=100.0 + index,
                high=105.0 + index,
                low=99.0 + index,
                close=103.0 + index,
                volume=1000.0 + index,
            )
            for index in range(4)
        ],
    )


def test_provider_loads_persisted_historical_market_data(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)

    repository = HistoricalMarketDataRepository(database)
    expected = _data()
    repository.save(expected)

    provider = RepositoryHistoricalDataProvider(
        repository=repository,
        timeframe="4h",
        source="binance",
    )

    result = provider.load("BTCUSDT")

    assert result.symbol == "BTCUSDT"
    assert result.timeframe == "4h"
    assert result.source == "binance"
    assert result.bars == expected.bars


def test_provider_preserves_requested_date_range(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)

    repository = HistoricalMarketDataRepository(database)
    data = _data()
    repository.save(data)

    provider = RepositoryHistoricalDataProvider(
        repository=repository,
        timeframe="4h",
        source="binance",
    )

    result = provider.load(
        "BTCUSDT",
        start=data.bars[1].timestamp,
        end=data.bars[3].timestamp,
    )

    assert result.bars == (
        data.bars[1],
        data.bars[2],
    )


def test_persisted_multi_timeframe_data_replays_without_future_bars(tmp_path):
    from atlas.trading.backtest_engine import BacktestEngine

    class RecordingLoop:
        def __init__(self):
            self.snapshots = []

        def process(self, snapshot):
            self.snapshots.append(snapshot)
            return snapshot

    database = Database(tmp_path / "atlas.db")
    initialize_database(database)
    repository = HistoricalMarketDataRepository(database)

    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    base = HistoricalMarketData(
        symbol="BTCUSDT",
        timeframe="4h",
        source="binance",
        bars=[
            OHLCVBar(
                timestamp=start + timedelta(hours=4 * index),
                open=100.0 + index,
                high=105.0 + index,
                low=99.0 + index,
                close=103.0 + index,
                volume=1000.0 + index,
            )
            for index in range(2)
        ],
    )

    hourly = HistoricalMarketData(
        symbol="BTCUSDT",
        timeframe="1h",
        source="binance",
        bars=[
            OHLCVBar(
                timestamp=start + timedelta(hours=index),
                open=100.0 + index,
                high=105.0 + index,
                low=99.0 + index,
                close=103.0 + index,
                volume=1000.0 + index,
            )
            for index in range(9)
        ],
    )

    repository.save(base)
    repository.save(hourly)

    base_provider = RepositoryHistoricalDataProvider(
        repository=repository,
        timeframe="4h",
        source="binance",
    )
    hourly_provider = RepositoryHistoricalDataProvider(
        repository=repository,
        timeframe="1h",
        source="binance",
    )

    base_history = base_provider.load("BTCUSDT")
    hourly_history = hourly_provider.load("BTCUSDT")

    loop = RecordingLoop()

    BacktestEngine().replay(
        base_history,
        loop=loop,
        warmup_bars=1,
        timeframe_data={
            "1h": hourly_history,
        },
    )

    assert len(loop.snapshots) == 2

    assert [
        candle.timestamp
        for candle in loop.snapshots[0].timeframe_candles["1h"]
    ] == [
        (start + timedelta(hours=index)).timestamp()
        for index in range(4)
    ]

    assert [
        candle.timestamp
        for candle in loop.snapshots[1].timeframe_candles["1h"]
    ] == [
        (start + timedelta(hours=index)).timestamp()
        for index in range(8)
    ]
