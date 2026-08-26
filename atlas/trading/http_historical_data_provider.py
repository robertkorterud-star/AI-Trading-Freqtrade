"""
ATLAS HTTP Historical Data Provider.

Generic transport layer for remote historical market data.

This module deliberately does not contain trading logic.
"""

from abc import ABC, abstractmethod
from datetime import datetime

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
)


class HTTPHistoricalDataProvider(
    ABC
):
    """Base class for HTTP-backed market data."""

    @abstractmethod
    def load(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> HistoricalMarketData:
        raise NotImplementedError
