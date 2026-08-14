"""
Market Search Service

Resolves common stock and cryptocurrency names/symbols
to ATLAS market symbols and enriches results with market data.
"""

from atlas.adapters.market_data import MarketDataAdapter


class MarketSearchService:
    """Searches and enriches the ATLAS market catalog."""

    MARKETS = [
        {
            "symbol": "BTC-USD",
            "name": "Bitcoin",
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

    def __init__(self) -> None:
        self.market = MarketDataAdapter()

    def search(self, query: str) -> list[dict]:
        """Return markets matching a name or symbol."""

        if not query:
            return []

        normalized = query.strip().lower()

        if not normalized:
            return []

        results = []

        for market in self.MARKETS:

            symbol = market["symbol"].lower()
            name = market["name"].lower()

            if not (
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
                            2,
                        ),
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

        return results
