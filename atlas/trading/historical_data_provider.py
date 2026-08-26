"""
ATLAS Historical Data Provider.

Common interface for historical market data sources.
"""

from abc import ABC, abstractmethod
from datetime import datetime

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
)


class HistoricalDataProvider(ABC):
    """Interface for historical market data providers."""

    @abstractmethod
    def load(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> HistoricalMarketData:
        """Load normalized historical OHLCV data."""
        raise NotImplementedError
