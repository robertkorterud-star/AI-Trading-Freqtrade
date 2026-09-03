"""
Market Search Service

Resolves common stock and cryptocurrency names/symbols
to ATLAS market symbols and enriches results with market data.
"""

from atlas.adapters.market_data import MarketDataAdapter
from atlas.market.asset_type import AssetType
from atlas.services.internet_asset_resolver import (
    InternetAssetResolver,
)
from atlas.services.yfinance_search_client import (
    YFinanceSearchClient,
)


class MarketSearchService:
    """Searches and enriches the ATLAS market catalog."""

    MARKETS = [
        {
            "symbol": "BTC-USD",
            "name": "Bitcoin",
            "type": "crypto",
        },
        {
            "symbol": "XRP-USD",
            "name": "XRP",
            "type": "crypto",
        },
        {
            "symbol": "ETH-USD",
            "name": "Ethereum",
            "type": "crypto",
        },
        {
            "symbol": "SOL-USD",
            "name": "Solana",
            "type": "crypto",
        },
        {
            "symbol": "NVDA",
            "name": "NVIDIA Corporation",
            "type": "stock",
        },
        {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "type": "stock",
        },
        {
            "symbol": "TSLA",
            "name": "Tesla, Inc.",
            "type": "stock",
        },
        {
            "symbol": "MSFT",
            "name": "Microsoft Corporation",
            "type": "stock",
        },
        {
            "symbol": "AMZN",
            "name": "Amazon.com, Inc.",
            "type": "stock",
        },
        {
            "symbol": "META",
            "name": "Meta Platforms, Inc.",
            "type": "stock",
        },
        {
            "symbol": "NVO",
            "name": "Novo Nordisk A/S",
            "type": "stock",
        },
    ]

    ALIASES = {
        "btc": "BTC-USD",
        "bitcoin": "BTC-USD",
        "btc-usd": "BTC-USD",
        "eth": "ETH-USD",
        "ethereum": "ETH-USD",
        "eth-usd": "ETH-USD",
        "sol": "SOL-USD",
        "solana": "SOL-USD",
        "sol-usd": "SOL-USD",
        "xrp": "XRP-USD",
        "ripple": "XRP-USD",
        "xrp-usd": "XRP-USD",
    }

    def __init__(self) -> None:
        self.market = MarketDataAdapter()

        self.internet_resolver = (
            InternetAssetResolver(
                search_client=YFinanceSearchClient()
            )
        )

    def search(self, query: str) -> list[dict]:
        """Return markets matching a name or symbol."""

        if not query:
            return []

        normalized = query.strip().lower()

        if not normalized:
            return []

        results = []

        resolved_symbol = self.ALIASES.get(
            normalized
        )

        for market in self.MARKETS:

            symbol = market["symbol"].lower()
            name = market["name"].lower()

            if resolved_symbol is not None:
                if market["symbol"] != resolved_symbol:
                    continue
            elif not (
                normalized == symbol
                or normalized == name
                or normalized in name
                or normalized in symbol
            ):
                continue

            result = market.copy()

            try:
                data = self.market.get(
                    market["symbol"]
                )

                result.update(
                    {
                        "price_usd": round(
                            data.price,
                            4,
                        ),
                        "currency": getattr(data, "currency", "USD"),
                        "change": round(
                            data.change_percent,
                            2,
                        ),
                        "ma20": round(
                            data.ma20,
                            2,
                        ),
                        "ma50": round(
                            data.ma50,
                            2,
                        ),
                    }
                )

            except Exception:
                result.update(
                    {
                        "price_usd": None,
                        "change": None,
                        "ma20": None,
                        "ma50": None,
                    }
                )

            results.append(result)

        if results:
            return results

        # Scanner v2 uses native Binance symbols such as SOLUSDT.
        # Resolve those directly so a Scanner candidate can open the
        # existing Market Terminal without requiring a separate catalog entry.
        normalized_upper = normalized.upper()
        for quote_asset in ("USDT", "USDC"):
            if normalized_upper.endswith(quote_asset) and len(normalized_upper) > len(quote_asset):
                base_asset = normalized_upper[: -len(quote_asset)]
                return [
                    {
                        "symbol": normalized_upper,
                        "name": base_asset,
                        "type": "crypto",
                        "market": "Binance",
                        "currency": quote_asset,
                        "price_usd": None,
                        "change": None,
                        "ma20": None,
                        "ma50": None,
                    }
                ]

        assets = self.internet_resolver.resolve(
            normalized
        )

        resolved_results = []

        for asset in assets:

            result = {
                "symbol": asset.symbol,
                "name": asset.name,
                "type": asset.asset_type.value,
            }

            try:
                data = self.market.get(
                    asset.symbol
                )

                result.update(
                    {
                        "price_usd": round(
                            data.price,
                            4,
                        ),
                        "currency": getattr(data, "currency", "USD"),
                        "change": round(
                            data.change_percent,
                            2,
                        ),
                        "ma20": round(
                            data.ma20,
                            2,
                        ),
                        "ma50": round(
                            data.ma50,
                            2,
                        ),
                    }
                )

            except Exception:
                result.update(
                    {
                        "price_usd": None,
                        "change": None,
                        "ma20": None,
                        "ma50": None,
                    }
                )

            resolved_results.append(result)

        return resolved_results
