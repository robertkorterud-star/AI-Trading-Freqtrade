"""
Technical Analysis Service
"""

from dataclasses import dataclass

from atlas.adapters.market_data import MarketDataAdapter


@dataclass
class TechnicalSnapshot:
    symbol: str
    price: float
    previous_close: float
    change_percent: float
    ma20: float
    ma50: float
    trend: str
    volume: float
    average_volume: float
    volume_ratio: float


class TechnicalService:
    """Provides technical market data."""

    def __init__(self, market_data=None):
        self.market = market_data or MarketDataAdapter()

    def get_snapshot(self, symbol: str) -> TechnicalSnapshot:
        if hasattr(self.market, "get_snapshot"):
            return self.market.get_snapshot(symbol)

        data = self.market.get(symbol)

        trend = self._trend(data)

        return TechnicalSnapshot(
            symbol=data.symbol,
            price=data.price,
            previous_close=data.previous_close,
            change_percent=data.change_percent,
            ma20=data.ma20,
            ma50=data.ma50,
            trend=trend,
            volume=data.volume,
            average_volume=data.average_volume,
            volume_ratio=data.volume_ratio,
        )

    def _trend(self, data):
        if data.price > data.ma20 > data.ma50:
            return "Bullish"

        if data.price < data.ma20 < data.ma50:
            return "Bearish"

        return "Neutral"
