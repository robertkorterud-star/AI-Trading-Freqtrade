"""
ATLAS Crypto Market Intelligence Service.
"""

from atlas.trading.crypto_intelligence_snapshot import (
    CryptoIntelligenceSnapshot,
)
from atlas.trading.historical_derivatives_data import (
    DerivativesFlowObservation,
)


class CryptoMarketIntelligenceService:
    """Build unified crypto market intelligence."""

    def __init__(
        self,
        crypto_market_service,
        breadth_analyzer,
        technical_analyzer=None,
        multi_timeframe_service=None,
    ):
        self.crypto_market_service = (
            crypto_market_service
        )

        self.breadth_analyzer = (
            breadth_analyzer
        )

        self.technical_analyzer = (
            technical_analyzer
        )

        self.multi_timeframe_service = (
            multi_timeframe_service
        )

    def analyze_with_market_data(
        self,
        coin_id: str,
        symbol: str,
        candles: list[dict],
    ) -> CryptoIntelligenceSnapshot:

        if self.technical_analyzer is None:
            raise RuntimeError(
                "Technical analyzer is not configured."
            )

        if self.multi_timeframe_service is None:
            raise RuntimeError(
                "Multi-timeframe service is not configured."
            )

        technical_result = (
            self.technical_analyzer.analyze(
                symbol,
                candles,
            )
        )

        if isinstance(
            technical_result,
            dict,
        ):
            technical_signal = str(
                technical_result.get(
                    "signal",
                    "WAIT",
                )
            ).upper()

            technical_confidence = float(
                technical_result.get(
                    "confidence",
                    0.0,
                )
            )

        else:
            technical_signal = str(
                technical_result
            ).upper()

            technical_confidence = 0.0

        mtf_result = (
            self.multi_timeframe_service.analyze(
                symbol
            )
        )

        multi_timeframe_signal = (
            str(
                mtf_result.overall_signal
            ).upper()
        )

        mtf_confidence = float(
            mtf_result.confidence
        )

        market_alignment = float(
            mtf_result.alignment
        )

        confidence = (
            (
                technical_confidence
                + mtf_confidence
            )
            / 2.0
        )

        return self.analyze(
            coin_id=coin_id,
            symbol=symbol,
            technical_signal=technical_signal,
            multi_timeframe_signal=(
                multi_timeframe_signal
            ),
            market_alignment=(
                market_alignment
            ),
            confidence=confidence,
        )


    def analyze(
        self,
        coin_id: str,
        symbol: str,
        technical_signal: str = "WAIT",
        multi_timeframe_signal: str = "WAIT",
        market_alignment: float = 0.0,
        confidence: float = 0.0,
        derivatives_flow: DerivativesFlowObservation | None = None,
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
            derivatives_flow=derivatives_flow,
        )
