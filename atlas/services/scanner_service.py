"""ATLAS Scanner service.

Coordinates market observations with the deterministic MarketScout.  The
service is deliberately market-data-vendor neutral and read-only: it finds
and explains candidates but never creates trading orders.
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

    @staticmethod
    def as_dict(result: ScannerResult) -> dict:
        """Return a dashboard/API-friendly representation of a scan result."""
        return {
            "scanned": result.scanned,
            "eligible": result.eligible,
            "candidates": [
                {
                    "symbol": item.symbol,
                    "asset_type": item.asset_type.value,
                    "score": item.score,
                    "momentum_score": item.momentum_score,
                    "volume_score": item.volume_score,
                    "breakout_score": item.breakout_score,
                    "catalyst_score": item.catalyst_score,
                    "liquidity_score": item.liquidity_score,
                    "reasons": list(item.reasons),
                }
                for item in result.candidates
            ],
        }
