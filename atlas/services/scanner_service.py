"""ATLAS Scanner service.

Coordinates market observations with the deterministic MarketScout. The service
is read-only: it finds and explains candidates but never creates trading
orders.
"""

from __future__ import annotations

from dataclasses import dataclass

from atlas.market.market_scout import MarketObservation, MarketScout, ScoutEvidence


@dataclass(frozen=True, slots=True)
class ScannerResult:
    """One scanner pass and its ranked candidates."""

    scanned: int
    eligible: int
    candidates: tuple[ScoutEvidence, ...]


class ScannerService:
    """Application service for ATLAS candidate discovery."""

    DEFAULT_CRYPTO_CANDIDATE_LIMIT = 100

    def __init__(self, scout: MarketScout | None = None) -> None:
        self.scout = scout or MarketScout()

    def scan(self, observations: list[MarketObservation]) -> ScannerResult:
        """Run one read-only scanner pass over market observations."""
        candidates = tuple(self.scout.scan(observations))
        return ScannerResult(
            scanned=len(observations),
            eligible=len(candidates),
            candidates=candidates,
        )

    def scan_crypto(
        self,
        provider,
        limit: int = DEFAULT_CRYPTO_CANDIDATE_LIMIT,
    ) -> ScannerResult:
        """Scan the provider crypto universe and retain its top candidates.

        Provider must expose get_crypto_observations(). Dependency injection
        keeps tests and alternative crypto sources independent of eToro keys.
        """
        observations = provider.get_crypto_observations()
        ranked = self.scout.scan(observations)
        return ScannerResult(
            scanned=len(observations),
            eligible=len(ranked),
            candidates=tuple(ranked[: max(0, int(limit))]),
        )

    def scan_etoro_crypto(
        self,
        limit: int = DEFAULT_CRYPTO_CANDIDATE_LIMIT,
    ) -> ScannerResult:
        """Scan all eToro crypto instruments using local environment keys."""
        from atlas.adapters.etoro_market_data import EtoroCryptoMarketDataProvider

        return self.scan_crypto(
            EtoroCryptoMarketDataProvider.from_env(),
            limit=limit,
        )

    def as_dict(self, result: ScannerResult) -> dict:
        """Return a stable dashboard/API representation of a scan result."""
        return {
            "scanned": result.scanned,
            "eligible": result.eligible,
            "rules": {
                "stock_min_price": self.scout.MIN_STOCK_PRICE,
                "minimum_average_volume": self.scout.MIN_AVERAGE_VOLUME,
                "minimum_current_volume": self.scout.MIN_VOLUME,
                "crypto_candidate_limit": self.DEFAULT_CRYPTO_CANDIDATE_LIMIT,
            },
            "candidates": [
                {
                    "symbol": item.symbol,
                    "asset_type": item.asset_type.value,
                    # Keep the explicit *_score fields as the canonical API
                    # values, while exposing short aliases for the dashboard.
                    "score": item.score,
                    "momentum_score": item.momentum_score,
                    "volume_score": item.volume_score,
                    "breakout_score": item.breakout_score,
                    "catalyst_score": item.catalyst_score,
                    "liquidity_score": item.liquidity_score,
                    "market": item.asset_type.value,
                    "momentum": item.momentum_score,
                    "volume": item.volume_score,
                    "breakout": item.breakout_score,
                    "catalyst": item.catalyst_score > 0,
                    "liquidity": item.liquidity_score,
                    "reasons": list(item.reasons),
                }
                for item in result.candidates
            ],
        }
