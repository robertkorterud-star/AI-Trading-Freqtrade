"""ATLAS Binance historical derivatives market-data provider.

Normalizes read-only Binance USD-M Futures funding-rate and open-interest
history into ATLAS derivatives market-data observations.
"""

from __future__ import annotations

from datetime import datetime, timezone

from atlas.adapters.binance_futures import BinanceFuturesAdapter
from atlas.trading.historical_derivatives_data import (
    FundingRateObservation,
    OpenInterestObservation,
)


class BinanceHistoricalDerivativesDataProvider:
    """Load normalized historical Binance USD-M derivatives data."""

    def __init__(
        self,
        adapter=None,
        funding_limit: int = 1000,
        open_interest_limit: int = 500,
    ):
        self.adapter = adapter or BinanceFuturesAdapter()
        self.funding_limit = funding_limit
        self.open_interest_limit = open_interest_limit

    def load_funding_rates(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> tuple[FundingRateObservation, ...]:
        start_time = self._to_milliseconds(start)
        end_time = self._to_milliseconds(end)

        if start_time is not None and end_time is not None:
            raw_observations = []
            next_start_time = start_time

            while next_start_time < end_time:
                page = self.adapter.get_funding_rate_history(
                    symbol=symbol,
                    start_time=next_start_time,
                    end_time=end_time,
                    limit=self.funding_limit,
                )

                if not page:
                    break

                page_last_time = int(page[-1]["fundingTime"])

                if (
                    raw_observations
                    and page_last_time
                    <= int(raw_observations[-1]["fundingTime"])
                ):
                    break

                raw_observations.extend(page)

                page_next_start_time = page_last_time + 1

                if page_next_start_time <= next_start_time:
                    break

                if len(page) < self.funding_limit:
                    break

                next_start_time = page_next_start_time
        else:
            raw_observations = (
                self.adapter.get_funding_rate_history(
                    symbol=symbol,
                    start_time=start_time,
                    end_time=end_time,
                    limit=self.funding_limit,
                )
            )

        return tuple(
            FundingRateObservation(
                timestamp=self._from_milliseconds(
                    observation["fundingTime"]
                ),
                funding_rate=float(
                    observation["fundingRate"]
                ),
                mark_price=float(
                    observation["markPrice"]
                ),
            )
            for observation in raw_observations
            if (
                end_time is None
                or int(observation["fundingTime"]) < end_time
            )
        )

    def load_open_interest(
        self,
        symbol: str,
        period: str = "5m",
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> tuple[OpenInterestObservation, ...]:
        start_time = self._to_milliseconds(start)
        end_time = self._to_milliseconds(end)

        raw_observations = (
            self.adapter.get_open_interest_history(
                symbol=symbol,
                period=period,
                start_time=start_time,
                end_time=end_time,
                limit=self.open_interest_limit,
            )
        )

        return tuple(
            OpenInterestObservation(
                timestamp=self._from_milliseconds(
                    observation["timestamp"]
                ),
                open_interest=float(
                    observation["sumOpenInterest"]
                ),
                open_interest_value=float(
                    observation["sumOpenInterestValue"]
                ),
            )
            for observation in raw_observations
            if (
                end_time is None
                or int(observation["timestamp"]) < end_time
            )
        )

    @staticmethod
    def _to_milliseconds(
        value: datetime | None,
    ) -> int | None:
        if value is None:
            return None

        return int(value.timestamp() * 1000)

    @staticmethod
    def _from_milliseconds(value) -> datetime:
        return datetime.fromtimestamp(
            int(value) / 1000.0,
            tz=timezone.utc,
        )
