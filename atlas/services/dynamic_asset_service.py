from atlas.market.asset_universe import AssetUniverse


class DynamicAssetService:
    """Resolve assets and add them to an active universe."""

    def __init__(
        self,
        resolver,
        universe: AssetUniverse,
        repository=None,
    ):
        self.resolver = resolver
        self.universe = universe
        self.repository = repository

    def _add_all(self, assets) -> int:
        added = 0

        for asset in assets:
            if not self.universe.add(asset):
                continue

            if self.repository is not None:
                self.repository.save(asset)

            added += 1

        return added

    def resolve_and_add(
        self,
        query: str,
    ) -> int:
        """Resolve a query and add newly discovered assets."""

        assets = self.resolver.resolve(query)

        return self._add_all(
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

        return self._add_all(
            exact_matches
        )
