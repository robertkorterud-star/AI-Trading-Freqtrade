"""Market-discovery candidate source for ATLAS."""

from atlas.market.asset_discovery import AssetDiscoveryService
from atlas.market.asset_universe import AssetUniverse
from atlas.market.candidates.source import Candidate
from atlas.market.trading_horizon import TradingHorizon


class MarketDiscoverySource:
    """Expose existing market discovery as the CandidateSource contract."""

    def __init__(
        self,
        discovery: AssetDiscoveryService,
        universe: AssetUniverse,
        limit: int | None = None,
        minimum_score: float = 0.0,
        horizon: TradingHorizon | None = None,
    ):
        self.discovery = discovery
        self.universe = universe
        self.limit = limit
        self.minimum_score = float(minimum_score)
        self.horizon = horizon

    def discover(self) -> list[Candidate]:
        """Discover and normalize market candidates."""

        discovered = self.discovery.discover(
            self.universe,
            limit=self.limit,
            horizon=self.horizon,
        )

        return [
            Candidate(
                symbol=result.symbol,
                source="market_discovery",
                score=float(result.score),
                reason="Market discovery score",
                metadata={
                    **(
                        {
                            "session": market_context.session,
                            "volatility_level": market_context.volatility_level,
                            "liquidity_level": market_context.liquidity_level,
                        }
                        if (market_context := getattr(result, "market_context", None)) is not None
                        else {}
                    ),
                    **(
                        {"horizon": result.horizon.value}
                        if getattr(result, "horizon", None) is not None
                        else {}
                    ),
                    **(
                        {
                            "volume_score": result.discovery_input.volume_score,
                            "momentum_score": result.discovery_input.momentum_score,
                            "volatility_score": result.discovery_input.volatility_score,
                            "news_score": result.discovery_input.news_score,
                            "liquidity_score": result.discovery_input.liquidity_score,
                        }
                        if getattr(result, "discovery_input", None) is not None
                        else {}
                    ),
                },
            )
            for result in discovered
            if float(result.score) >= self.minimum_score
        ]
