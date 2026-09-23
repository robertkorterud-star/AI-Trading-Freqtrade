"""Market-discovery candidate source for ATLAS."""

from atlas.market.asset_discovery import AssetDiscoveryService
from atlas.market.asset_universe import AssetUniverse
from atlas.market.candidates.source import Candidate


class MarketDiscoverySource:
    """Expose existing market discovery as the CandidateSource contract."""

    def __init__(
        self,
        discovery: AssetDiscoveryService,
        universe: AssetUniverse,
        limit: int | None = None,
        minimum_score: float = 0.0,
    ):
        self.discovery = discovery
        self.universe = universe
        self.limit = limit
        self.minimum_score = float(minimum_score)

    def discover(self) -> list[Candidate]:
        """Discover and normalize market candidates."""

        discovered = self.discovery.discover(
            self.universe,
            limit=self.limit,
        )

        return [
            Candidate(
                symbol=result.symbol,
                source="market_discovery",
                score=float(result.score),
                reason="Market discovery score",
                metadata=(
                    {
                        "session": market_context.session,
                        "volatility_level": market_context.volatility_level,
                        "liquidity_level": market_context.liquidity_level,
                    }
                    if (market_context := getattr(result, "market_context", None)) is not None
                    else {}
                ),
            )
            for result in discovered
            if float(result.score) >= self.minimum_score
        ]
