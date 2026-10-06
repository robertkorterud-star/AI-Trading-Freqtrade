from datetime import datetime, timezone

from atlas.adapters.binance_historical_derivatives_data import (
    BinanceHistoricalDerivativesDataProvider,
)
from atlas.trading.historical_derivatives_data import (
    FundingRateObservation,
    OpenInterestObservation,
)


def test_provider_normalizes_funding_rate_history():
    class FakeAdapter:
        def get_funding_rate_history(
            self,
            symbol,
            start_time=None,
            end_time=None,
            limit=100,
        ):
            return [
                {
                    "symbol": symbol,
                    "fundingTime": 1767225600000,
                    "fundingRate": "0.00010000",
                    "markPrice": "93450.0",
                }
            ]

    provider = BinanceHistoricalDerivativesDataProvider(
        adapter=FakeAdapter()
    )

    result = provider.load_funding_rates(
        symbol="BTCUSDT",
        start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    assert result == (
        FundingRateObservation(
            timestamp=datetime(
                2026,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            funding_rate=0.0001,
            mark_price=93450.0,
        ),
    )


def test_provider_normalizes_open_interest_history():
    class FakeAdapter:
        def get_open_interest_history(
            self,
            symbol,
            period="5m",
            start_time=None,
            end_time=None,
            limit=100,
        ):
            return [
                {
                    "symbol": symbol,
                    "sumOpenInterest": "95312.78",
                    "sumOpenInterestValue": "8122126905.81",
                    "timestamp": 1767225600000,
                }
            ]

    provider = BinanceHistoricalDerivativesDataProvider(
        adapter=FakeAdapter()
    )

    result = provider.load_open_interest(
        symbol="BTCUSDT",
        period="5m",
        start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    assert result == (
        OpenInterestObservation(
            timestamp=datetime(
                2026,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            open_interest=95312.78,
            open_interest_value=8122126905.81,
        ),
    )


def test_funding_paginates_without_duplicate_boundary():
    class PaginatedAdapter:
        def __init__(self):
            self.calls = []

        def get_funding_rate_history(
            self,
            symbol,
            start_time=None,
            end_time=None,
            limit=100,
        ):
            self.calls.append(start_time)

            if len(self.calls) == 1:
                return [
                    {
                        "symbol": symbol,
                        "fundingTime": 1767225600000,
                        "fundingRate": "0.0001",
                        "markPrice": "93450.0",
                    },
                    {
                        "symbol": symbol,
                        "fundingTime": 1767254400000,
                        "fundingRate": "0.0002",
                        "markPrice": "94000.0",
                    },
                ]

            if len(self.calls) == 2:
                return [
                    {
                        "symbol": symbol,
                        "fundingTime": 1767283200000,
                        "fundingRate": "-0.0001",
                        "markPrice": "93800.0",
                    }
                ]

            return []

    adapter = PaginatedAdapter()
    provider = BinanceHistoricalDerivativesDataProvider(
        adapter=adapter,
        funding_limit=2,
    )

    result = provider.load_funding_rates(
        symbol="BTCUSDT",
        start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    assert len(result) == 3
    assert adapter.calls == [
        1767225600000,
        1767254400001,
    ]


def test_funding_pagination_stops_when_no_progress():
    class NoProgressAdapter:
        def __init__(self):
            self.calls = 0

        def get_funding_rate_history(
            self,
            symbol,
            start_time=None,
            end_time=None,
            limit=100,
        ):
            self.calls += 1

            if self.calls > 2:
                raise AssertionError(
                    "pagination continued without progress"
                )

            return [
                {
                    "symbol": symbol,
                    "fundingTime": 1767225600000,
                    "fundingRate": "0.0001",
                    "markPrice": "93450.0",
                }
            ]

    adapter = NoProgressAdapter()
    provider = BinanceHistoricalDerivativesDataProvider(
        adapter=adapter,
        funding_limit=1,
    )

    result = provider.load_funding_rates(
        symbol="BTCUSDT",
        start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    assert len(result) == 1
    assert adapter.calls == 2


def test_funding_excludes_observation_at_end_boundary():
    class FakeAdapter:
        def get_funding_rate_history(
            self,
            symbol,
            start_time=None,
            end_time=None,
            limit=100,
        ):
            return [
                {
                    "symbol": symbol,
                    "fundingTime": 1767225600000,
                    "fundingRate": "0.0001",
                    "markPrice": "93450.0",
                },
                {
                    "symbol": symbol,
                    "fundingTime": 1767312000000,
                    "fundingRate": "0.0002",
                    "markPrice": "94000.0",
                },
            ]

    provider = BinanceHistoricalDerivativesDataProvider(
        adapter=FakeAdapter()
    )

    result = provider.load_funding_rates(
        symbol="BTCUSDT",
        start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    assert len(result) == 1
    assert result[0].timestamp == datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )


def test_open_interest_excludes_observation_at_end_boundary():
    class FakeAdapter:
        def get_open_interest_history(
            self,
            symbol,
            period="5m",
            start_time=None,
            end_time=None,
            limit=100,
        ):
            return [
                {
                    "symbol": symbol,
                    "sumOpenInterest": "95312.78",
                    "sumOpenInterestValue": "8122126905.81",
                    "timestamp": 1767225600000,
                },
                {
                    "symbol": symbol,
                    "sumOpenInterest": "96000.0",
                    "sumOpenInterestValue": "8200000000.0",
                    "timestamp": 1767312000000,
                },
            ]

    provider = BinanceHistoricalDerivativesDataProvider(
        adapter=FakeAdapter()
    )

    result = provider.load_open_interest(
        symbol="BTCUSDT",
        period="5m",
        start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    assert len(result) == 1
    assert result[0].timestamp == datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )


def test_open_interest_paginates_backward_without_duplicate_boundary():
    class FakeAdapter:
        def __init__(self):
            self.calls = []

        def get_open_interest_history(
            self,
            symbol,
            period="5m",
            start_time=None,
            end_time=None,
            limit=100,
        ):
            self.calls.append(
                {
                    "symbol": symbol,
                    "period": period,
                    "start_time": start_time,
                    "end_time": end_time,
                    "limit": limit,
                }
            )

            if len(self.calls) == 1:
                return [
                    {
                        "symbol": symbol,
                        "sumOpenInterest": "103.0",
                        "sumOpenInterestValue": "1030.0",
                        "timestamp": 1767226500000,
                    },
                    {
                        "symbol": symbol,
                        "sumOpenInterest": "104.0",
                        "sumOpenInterestValue": "1040.0",
                        "timestamp": 1767226800000,
                    },
                ]

            if len(self.calls) == 2:
                return [
                    {
                        "symbol": symbol,
                        "sumOpenInterest": "101.0",
                        "sumOpenInterestValue": "1010.0",
                        "timestamp": 1767225900000,
                    },
                    {
                        "symbol": symbol,
                        "sumOpenInterest": "102.0",
                        "sumOpenInterestValue": "1020.0",
                        "timestamp": 1767226200000,
                    },
                ]

            return []

    adapter = FakeAdapter()
    provider = BinanceHistoricalDerivativesDataProvider(
        adapter=adapter,
        open_interest_limit=2,
    )

    result = provider.load_open_interest(
        symbol="BTCUSDT",
        period="5m",
        start=datetime(
            2026,
            1,
            1,
            0,
            5,
            tzinfo=timezone.utc,
        ),
        end=datetime(
            2026,
            1,
            1,
            0,
            25,
            tzinfo=timezone.utc,
        ),
    )

    assert [
        observation.timestamp
        for observation in result
    ] == [
        datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 0, 10, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 0, 15, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 0, 20, tzinfo=timezone.utc),
    ]

    assert len(adapter.calls) == 2
    assert adapter.calls[1]["end_time"] == 1767226500000 - 1
