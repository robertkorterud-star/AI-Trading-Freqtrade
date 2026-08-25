import yfinance as yf


class YFinanceSearchClient:
    """Search Yahoo Finance for market instruments."""

    def search(self, query: str) -> list[dict]:
        query = (query or "").strip()

        if not query:
            return []

        search = yf.Search(query)

        return list(
            getattr(
                search,
                "quotes",
                [],
            )
        )
