from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from atlas.market.asset import Asset
from atlas.market.asset_universe import AssetUniverse


@dataclass(slots=True, frozen=True)
class DiscoveryInput:
    """Market signals used to score an asset."""

    volume_score: float = 0.0
    momentum_score: float = 0.0
    volatility_score: float = 0.0
    news_score: float = 0.0
    liquidity_score: float = 0.0


@dataclass(slots=True, frozen=True)
class DiscoveryScore:
    """Discovery score for one asset."""

    asset: Asset
    score: float

    @property
    def symbol(self):
        return self.asset.symbol


class AssetDiscoveryService:
    """Ranks assets by market-discovery relevance."""

    VOLUME_WEIGHT = 0.20
    MOMENTUM_WEIGHT = 0.20
    VOLATILITY_WEIGHT = 0.20
    NEWS_WEIGHT = 0.20
    LIQUIDITY_WEIGHT = 0.20
    DEFAULT_DISCOVERY_WORKERS = 8

    def __init__(self, market_data=None):
        self.market_data = market_data

    @classmethod
    def _clamp(cls, value: float) -> float:
        return max(
            0.0,
            min(
                100.0,
                float(value),
            ),
        )

    def score(
        self,
        asset: Asset,
        signals: DiscoveryInput,
    ) -> DiscoveryScore:
        """Calculate a normalized discovery score."""

        score = (
            self._clamp(signals.volume_score)
            * self.VOLUME_WEIGHT
            + self._clamp(signals.momentum_score)
            * self.MOMENTUM_WEIGHT
            + self._clamp(signals.volatility_score)
            * self.VOLATILITY_WEIGHT
            + self._clamp(signals.news_score)
            * self.NEWS_WEIGHT
            + self._clamp(signals.liquidity_score)
            * self.LIQUIDITY_WEIGHT
        )

        return DiscoveryScore(
            asset=asset,
            score=round(score, 2),
        )

    def market_input(self, asset: Asset) -> DiscoveryInput:
        """Convert market data into discovery signals."""

        if self.market_data is None:
            raise ValueError(
                "A market data provider is required."
            )

        data = self.market_data.get(
            asset.symbol
        )

        if data is None:
            return DiscoveryInput()

        volume_score = (
            self._clamp(
                float(data.volume_ratio) * 50.0
            )
        )

        momentum_score = self._clamp(
            (
                (
                    float(data.price) / float(data.ma50)
                )
                - 1.0
            ) * 1000.0
        )

        volatility_score = self._clamp(
            abs(float(data.change_percent)) * 10.0
        )

        liquidity_score = self._clamp(
            float(data.volume_ratio) * 50.0
        )

        return DiscoveryInput(
            volume_score=volume_score,
            momentum_score=momentum_score,
            volatility_score=volatility_score,
            news_score=0.0,
            liquidity_score=liquidity_score,
        )

    def discover(
        self,
        universe: AssetUniverse,
        limit: int | None = None,
    ) -> list[DiscoveryScore]:
        """Build discovery inputs from market data and rank assets."""

        if self.market_data is None:
            raise ValueError(
                "A market data provider is required."
            )

        assets = universe.all()
        market_data = {}
        workers = min(self.DEFAULT_DISCOVERY_WORKERS, len(assets))

        if workers == 1:
            for asset in assets:
                try:
                    market_data[asset.symbol] = self.market_input(asset)
                except Exception:
                    continue
        else:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(self.market_input, asset): asset
                    for asset in assets
                }
                for future in as_completed(futures):
                    asset = futures[future]
                    try:
                        market_data[asset.symbol] = future.result()
                    except Exception:
                        continue

        available_assets = [
            asset
            for asset in universe.all()
            if asset.symbol in market_data
        ]

        if not available_assets:
            return []

        available_universe = AssetUniverse(
            assets=available_assets
        )

        return self.rank(
            available_universe,
            market_data,
            limit=limit,
        )

    def rank(
        self,
        universe: AssetUniverse,
        market_data: dict[str, DiscoveryInput],
        limit: int | None = None,
    ) -> list[DiscoveryScore]:
        """Rank all active assets by discovery score."""

        results = [
            self.score(
                asset,
                market_data.get(
                    asset.symbol,
                    DiscoveryInput(),
                ),
            )
            for asset in universe.all()
        ]

        results.sort(
            key=lambda result: (
                result.score,
                result.symbol,
            ),
            reverse=True,
        )

        if limit is not None:
            return results[:max(0, limit)]

        return results
