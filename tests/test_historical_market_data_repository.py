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


def _data():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    bars = [
        OHLCVBar(
            timestamp=start + timedelta(hours=4 * index),
            open=100.0 + index,
            high=105.0 + index,
            low=99.0 + index,
            close=103.0 + index,
            volume=1000.0 + index,
        )
        for index in range(3)
    ]

    return HistoricalMarketData(
        symbol="BTCUSDT",
        bars=bars,
        timeframe="4h",
        source="binance",
    )


def test_repository_round_trips_historical_market_data(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)

    repository = HistoricalMarketDataRepository(database)
    expected = _data()

    repository.save(expected)

    result = repository.load(
        symbol="BTCUSDT",
        timeframe="4h",
        source="binance",
    )

    assert result.symbol == expected.symbol
    assert result.timeframe == expected.timeframe
    assert result.source == expected.source
    assert result.bars == expected.bars


def test_repository_save_is_idempotent(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)

    repository = HistoricalMarketDataRepository(database)
    data = _data()

    repository.save(data)
    repository.save(data)

    result = repository.load(
        symbol="BTCUSDT",
        timeframe="4h",
        source="binance",
    )

    assert len(result.bars) == len(data.bars)
    assert result.bars == data.bars


def test_repository_filters_requested_date_range(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)

    repository = HistoricalMarketDataRepository(database)
    data = _data()
    repository.save(data)

    result = repository.load(
        symbol="BTCUSDT",
        timeframe="4h",
        source="binance",
        start=data.bars[1].timestamp,
        end=data.bars[2].timestamp,
    )

    assert result.bars == (data.bars[1],)
