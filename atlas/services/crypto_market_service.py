"""
ATLAS Crypto Market Service.

Coordinates CoinGecko data retrieval and converts external
responses into normalized ATLAS crypto market contexts.
"""

from atlas.trading.crypto_market_context import (
    CryptoAssetContext,
    CryptoMarketContextBuilder,
    GlobalCryptoContext,
)


class CryptoMarketService:
    """Build normalized crypto market contexts."""

    def __init__(
        self,
        coingecko,
        context_builder=None,
    ):
        self.coingecko = coingecko
        self.context_builder = (
            context_builder
            or CryptoMarketContextBuilder()
        )

    def get_asset(
        self,
        coin_id: str,
    ) -> CryptoAssetContext:

        data = self.coingecko.get_coin(
            coin_id
        )

        return self.context_builder.asset_from_coin(
            data
        )

    def get_market_asset(
        self,
        data: dict,
    ) -> CryptoAssetContext:

        return self.context_builder.asset_from_market(
            data
        )

    def get_markets(
        self,
        vs_currency: str = "usd",
        page: int = 1,
        per_page: int = 100,
    ) -> list[CryptoAssetContext]:

        data = self.coingecko.get_markets(
            vs_currency=vs_currency,
            page=page,
            per_page=per_page,
        )

        return [
            self.context_builder.asset_from_market(
                item
            )
            for item in data
        ]

    def get_global_context(
        self,
    ) -> GlobalCryptoContext:

        data = self.coingecko.get_global_market()

        return self.context_builder.global_context(
            data
        )
