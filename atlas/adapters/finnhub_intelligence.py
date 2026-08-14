"""
Finnhub Intelligence Adapter

Fetches company news from Finnhub for ATLAS research.
"""

import os
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()


class FinnhubIntelligenceAdapter:
    """Fetches company intelligence from Finnhub."""

    BASE_URL = "https://finnhub.io/api/v1/company-news"

    def __init__(self) -> None:
        self.api_key = os.getenv("FINNHUB_API_KEY")

    def search(self, symbol: str) -> list[dict]:
        """Fetch recent company news for a symbol."""

        if not self.api_key:
            return []

        today = date.today()
        start = today - timedelta(days=7)

        try:
            response = requests.get(
                self.BASE_URL,
                params={
                    "symbol": symbol,
                    "from": start.isoformat(),
                    "to": today.isoformat(),
                    "token": self.api_key,
                },
                timeout=10,
            )

            response.raise_for_status()
            articles = response.json()

        except Exception:
            return []

        results = []

        for article in articles:

            results.append(
                {
                    "source": "Finnhub",
                    "title": article.get(
                        "headline",
                        "",
                    ),
                    "summary": article.get(
                        "summary",
                        "",
                    ),
                    "sentiment": "neutral",
                    "url": article.get(
                        "url",
                        "",
                    ),
                    "published_at": article.get(
                        "datetime",
                        "",
                    ),
                }
            )

        return results
