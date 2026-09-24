from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import time

from atlas.market.asset import Asset
from atlas.market.asset_universe import AssetUniverse
from atlas.market.market_context import MarketContext, MarketContextService
from atlas.market.trading_horizon import TradingHorizon


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
    market_context: MarketContext | None = None
    discovery_input: DiscoveryInput | None = None
    horizon: TradingHorizon | None = None

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
        horizon: TradingHorizon | None = None,
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
            horizon=horizon,
        )

    def _market_input_from_data(self, asset: Asset, data) -> DiscoveryInput:
        if data is None:
            return DiscoveryInput()

        volume_score = self._clamp(float(data.volume_ratio) * 50.0)
        momentum_score = self._clamp(
            ((float(data.price) / float(data.ma50)) - 1.0) * 1000.0
        )
        volatility_score = self._clamp(abs(float(data.change_percent)) * 10.0)
        liquidity_score = self._clamp(float(data.volume_ratio) * 50.0)

        return DiscoveryInput(
            volume_score=volume_score,
            momentum_score=momentum_score,
            volatility_score=volatility_score,
            news_score=0.0,
            liquidity_score=liquidity_score,
        )

    def market_input(self, asset: Asset) -> DiscoveryInput:
        """Convert market data into discovery signals."""
        if self.market_data is None:
            raise ValueError("A market data provider is required.")
        return self._market_input_from_data(
            asset,
            self.market_data.get(asset.symbol),
        )

    def discover(
        self,
        universe: AssetUniverse,
        limit: int | None = None,
        timestamp: float | None = None,
    ) -> list[DiscoveryScore]:
        """Build discovery inputs from market data and rank assets."""

        if self.market_data is None:
            raise ValueError(
                "A market data provider is required."
            )

        assets = universe.all()
        context_timestamp = time.time() if timestamp is None else float(timestamp)
        market_data = {}

        get_many = getattr(self.market_data, "get_many", None)
        if callable(get_many):
            try:
                batch = get_many([asset.symbol for asset in assets])
            except Exception:
                batch = {}
            for asset in assets:
                data = batch.get(asset.symbol)
                if data is not None:
                    market_data[asset.symbol] = self._market_input_from_data(
                        asset,
                        data,
                    )
        else:
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

        results = self.rank(
            available_universe,
            market_data,
            limit=limit,
        )

        data_by_symbol = {
            asset.symbol: market_data[asset.symbol]
            for asset in available_assets
        }
        return [
            DiscoveryScore(
                asset=result.asset,
                score=result.score,
                market_context=MarketContextService.build(
                    asset_type=result.asset.asset_type,
                    timestamp=context_timestamp,
                    change_percent=data_by_symbol[result.symbol].volatility_score / 10.0,
                    volume_ratio=data_by_symbol[result.symbol].liquidity_score / 50.0,
                ),
                discovery_input=data_by_symbol[result.symbol],
            )
            for result in results
        ]

    def rank(
        self,
        universe: AssetUniverse,
        market_data: dict[str, DiscoveryInput],
        limit: int | None = None,
        horizon: TradingHorizon | None = None,
    ) -> list[DiscoveryScore]:
        """Rank all active assets by discovery score."""

        results = [
            self.score(
                asset,
                market_data.get(
                    asset.symbol,
                    DiscoveryInput(),
                ),
                horizon=horizon,
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
