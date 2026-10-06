"""
ATLAS Crypto Intelligence Context Bridge.

Exposes crypto market intelligence to downstream decision
systems without making or changing trading decisions.
"""

from dataclasses import dataclass

from atlas.trading.crypto_intelligence_snapshot import (
    CryptoIntelligenceSnapshot,
)
from atlas.trading.historical_derivatives_data import (
    DerivativesFlowObservation,
)


@dataclass(slots=True)
class CryptoIntelligenceContext:
    symbol: str

    asset_change_24h: float | None
    asset_market_cap_rank: int | None

    technical_signal: str
    multi_timeframe_signal: str

    market_regime: str
    advance_ratio: float
    decline_ratio: float

    btc_dominance: float | None
    eth_dominance: float | None
    market_cap_change_24h: float | None

    market_alignment: float
    confidence: float

    data_quality: str
    actionable: bool

    derivatives_flow: DerivativesFlowObservation | None = None


class CryptoIntelligenceContextBridge:
    """Convert a snapshot into a decision-ready context."""

    @staticmethod
    def build(
        snapshot: CryptoIntelligenceSnapshot,
    ) -> CryptoIntelligenceContext:

        return CryptoIntelligenceContext(
            symbol=snapshot.symbol,

            asset_change_24h=(
                snapshot.asset.change_24h
            ),
            asset_market_cap_rank=(
                snapshot.asset.market_cap_rank
            ),

            technical_signal=(
                snapshot.technical_signal
            ),
            multi_timeframe_signal=(
                snapshot.multi_timeframe_signal
            ),

            market_regime=(
                snapshot.market_regime
            ),
            advance_ratio=(
                snapshot.breadth.advance_ratio
            ),
            decline_ratio=(
                snapshot.breadth.decline_ratio
            ),

            btc_dominance=(
                snapshot.global_market.btc_dominance
            ),
            eth_dominance=(
                snapshot.global_market.eth_dominance
            ),
            market_cap_change_24h=(
                snapshot.global_market
                .market_cap_change_24h
            ),

            market_alignment=(
                snapshot.market_alignment
            ),
            confidence=snapshot.confidence,

            data_quality=snapshot.data_quality,
            actionable=snapshot.is_actionable,
            derivatives_flow=snapshot.derivatives_flow,
        )
