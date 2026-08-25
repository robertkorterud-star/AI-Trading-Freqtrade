from atlas.market.asset import Asset
from atlas.market.asset_type import AssetType


class InternetAssetResolver:
    """Resolve unknown assets using an external search source."""

    QUOTE_TYPE_MAP = {
        "EQUITY": AssetType.STOCK,
        "ETF": AssetType.ETF,
        "CRYPTOCURRENCY": AssetType.CRYPTO,
    }

    def __init__(self, search_client):
        self.search_client = search_client

    def resolve(
        self,
        query: str,
    ) -> list[Asset]:
        """Resolve a search query into ATLAS assets."""

        normalized = (query or "").strip()

        if not normalized:
            return []

        raw_results = self.search_client.search(
            normalized
        )

        assets = []
        seen = set()

        for result in raw_results:

            symbol = str(
                result.get("symbol", "")
            ).strip()

            if not symbol or symbol in seen:
                continue

            quote_type = str(
                result.get("quoteType", "")
            ).upper()

            asset_type = self.QUOTE_TYPE_MAP.get(
                quote_type
            )

            if asset_type is None:
                continue

            name = (
                result.get("longname")
                or result.get("shortname")
                or symbol
            )

            exchange = (
                result.get("exchange")
                or result.get("exchDisp")
                or "unknown"
            )

            currency = (
                result.get("currency")
                or "USD"
            )

            assets.append(
                Asset(
                    symbol=symbol,
                    name=name,
                    asset_type=asset_type,
                    market=str(exchange),
                    currency=str(currency),
                )
            )

            seen.add(symbol)

        return assets
