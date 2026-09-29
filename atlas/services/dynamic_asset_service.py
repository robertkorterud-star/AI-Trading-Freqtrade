from atlas.market.asset_universe import AssetUniverse


class DynamicAssetService:
    """Resolve assets and add them to an active universe."""

    def __init__(
        self,
        resolver,
        universe: AssetUniverse,
    ):
        self.resolver = resolver
        self.universe = universe

    def resolve_and_add(
        self,
        query: str,
    ) -> int:
        """Resolve a query and add newly discovered assets."""

        assets = self.resolver.resolve(query)

        return self.universe.add_all(
            assets
        )

    def resolve_and_add_symbol(
        self,
        symbol: str,
    ) -> int:
        """Resolve and add only the explicitly requested symbol."""

        normalized = (symbol or "").strip().upper()

        if not normalized:
            return 0

        assets = self.resolver.resolve(normalized)

        exact_matches = [
            asset
            for asset in assets
            if asset.symbol.strip().upper() == normalized
        ]

        return self.universe.add_all(
            exact_matches
        )
