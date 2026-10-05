"""Historical data provider backed by persistent ATLAS market data."""

from datetime import datetime

from atlas.database.historical_market_data_repository import (
    HistoricalMarketDataRepository,
)
from atlas.trading.historical_data_provider import HistoricalDataProvider
from atlas.trading.historical_market_data import HistoricalMarketData


class RepositoryHistoricalDataProvider(HistoricalDataProvider):
    """Load canonical historical market data from persistent storage."""

    def __init__(
        self,
        repository: HistoricalMarketDataRepository,
        timeframe: str,
        source: str,
    ) -> None:
        self.repository = repository
        self.timeframe = timeframe
        self.source = source

    def load(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> HistoricalMarketData:
        return self.repository.load(
            symbol=symbol,
            timeframe=self.timeframe,
            source=self.source,
            start=start,
            end=end,
        )
