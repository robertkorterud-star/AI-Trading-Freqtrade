"""
ATLAS Crypto Market Intelligence Service.
"""

from atlas.trading.crypto_intelligence_snapshot import (
    CryptoIntelligenceSnapshot,
)


class CryptoMarketIntelligenceService:
    """Build unified crypto market intelligence."""

    def __init__(
        self,
        crypto_market_service,
        breadth_analyzer,
    ):
        self.crypto_market_service = (
            crypto_market_service
        )
        self.breadth_analyzer = breadth_analyzer

    def analyze(
        self,
        coin_id: str,
        symbol: str,
        technical_signal: str = "WAIT",
        multi_timeframe_signal: str = "WAIT",
        market_alignment: float = 0.0,
        confidence: float = 0.0,
    ) -> CryptoIntelligenceSnapshot:

        asset = (
            self.crypto_market_service.get_asset(
                coin_id
            )
        )

        global_market = (
            self.crypto_market_service.get_global_context()
        )

        assets = (
            self.crypto_market_service.get_markets()
        )

        breadth = self.breadth_analyzer.analyze(
            assets
        )

        return CryptoIntelligenceSnapshot.build(
            symbol=symbol,
            asset=asset,
            global_market=global_market,
            breadth=breadth,
            technical_signal=technical_signal,
            multi_timeframe_signal=(
                multi_timeframe_signal
            ),
            market_alignment=market_alignment,
            confidence=confidence,
        )
