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
