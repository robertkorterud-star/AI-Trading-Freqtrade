"""
ATLAS Crypto Intelligence Snapshot.

Combines crypto asset context, global crypto context,
market breadth and optional technical / multi-timeframe
analysis into one read-only market intelligence object.

This model does not make trading decisions.
"""

from dataclasses import dataclass

from atlas.trading.crypto_market_breadth import (
    CryptoMarketBreadth,
)
from atlas.trading.crypto_market_context import (
    CryptoAssetContext,
    GlobalCryptoContext,
)


@dataclass(slots=True)
class CryptoIntelligenceSnapshot:
    symbol: str

    asset: CryptoAssetContext
    global_market: GlobalCryptoContext
    breadth: CryptoMarketBreadth

    technical_signal: str
    multi_timeframe_signal: str

    market_alignment: float
    confidence: float

    data_quality: str

    @property
    def market_regime(self) -> str:
        return self.breadth.breadth_regime

    @property
    def is_actionable(self) -> bool:
        return (
            self.data_quality == "GOOD"
            and self.confidence > 0
            and self.multi_timeframe_signal
            in {
                "BUY",
                "SELL",
            }
        )

    @classmethod
    def build(
        cls,
        symbol: str,
        asset: CryptoAssetContext,
        global_market: GlobalCryptoContext,
        breadth: CryptoMarketBreadth,
        technical_signal: str = "WAIT",
        multi_timeframe_signal: str = "WAIT",
        market_alignment: float = 0.0,
        confidence: float = 0.0,
    ) -> "CryptoIntelligenceSnapshot":

        quality = cls._quality(
            asset.data_quality,
            global_market.data_quality,
            breadth.data_quality,
        )

        if quality != "GOOD":
            confidence = 0.0
            market_alignment = 0.0

        return cls(
            symbol=symbol,
            asset=asset,
            global_market=global_market,
            breadth=breadth,
            technical_signal=technical_signal,
            multi_timeframe_signal=multi_timeframe_signal,
            market_alignment=market_alignment,
            confidence=confidence,
            data_quality=quality,
        )

    @staticmethod
    def _quality(
        asset_quality: str,
        global_quality: str,
        breadth_quality: str,
    ) -> str:

        qualities = {
            asset_quality,
            global_quality,
            breadth_quality,
        }

        if "MISSING" in qualities:
            return "MISSING"

        if "POOR" in qualities:
            return "POOR"

        if "PARTIAL" in qualities:
            return "PARTIAL"

        return "GOOD"
