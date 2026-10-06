from datetime import datetime, timedelta, timezone

from atlas.database.connection import Database
from atlas.database.derivatives_market_data_repository import (
    DerivativesMarketDataRepository,
)
from atlas.database.schema import initialize_database
from atlas.trading.historical_derivatives_data import (
    FundingRateObservation,
    OpenInterestObservation,
)


def test_repository_round_trips_funding_rates(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)
    repository = DerivativesMarketDataRepository(database)

    observations = [
        FundingRateObservation(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            funding_rate=0.0001,
            mark_price=93450.0,
        ),
        FundingRateObservation(
            timestamp=datetime(2026, 1, 1, 8, tzinfo=timezone.utc),
            funding_rate=-0.0002,
            mark_price=94000.0,
        ),
    ]

    repository.save_funding_rates(
        symbol="BTCUSDT",
        source="binance_futures",
        observations=observations,
    )

    result = repository.load_funding_rates(
        symbol="BTCUSDT",
        source="binance_futures",
    )

    assert result == tuple(observations)


def test_repository_round_trips_open_interest(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)
    repository = DerivativesMarketDataRepository(database)

    observations = [
        OpenInterestObservation(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            open_interest=95312.78,
            open_interest_value=8122126905.81,
        ),
        OpenInterestObservation(
            timestamp=datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc),
            open_interest=95400.0,
            open_interest_value=8130000000.0,
        ),
    ]

    repository.save_open_interest(
        symbol="BTCUSDT",
        source="binance_futures",
        period="5m",
        observations=observations,
    )

    result = repository.load_open_interest(
        symbol="BTCUSDT",
        source="binance_futures",
        period="5m",
    )

    assert result == tuple(observations)


def test_repository_saves_derivatives_data_idempotently(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)
    repository = DerivativesMarketDataRepository(database)

    funding = [
        FundingRateObservation(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            funding_rate=0.0001,
            mark_price=93450.0,
        )
    ]

    repository.save_funding_rates(
        "BTCUSDT",
        "binance_futures",
        funding,
    )
    repository.save_funding_rates(
        "BTCUSDT",
        "binance_futures",
        funding,
    )

    assert len(
        repository.load_funding_rates(
            "BTCUSDT",
            "binance_futures",
        )
    ) == 1


def test_repository_filters_open_interest_date_range(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)
    repository = DerivativesMarketDataRepository(database)

    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    observations = [
        OpenInterestObservation(
            timestamp=start + timedelta(minutes=5 * index),
            open_interest=95000.0 + index,
            open_interest_value=8_000_000_000.0 + index,
        )
        for index in range(3)
    ]

    repository.save_open_interest(
        "BTCUSDT",
        "binance_futures",
        "5m",
        observations,
    )

    result = repository.load_open_interest(
        symbol="BTCUSDT",
        source="binance_futures",
        period="5m",
        start=observations[1].timestamp,
        end=observations[2].timestamp,
    )

    assert result == (observations[1],)
