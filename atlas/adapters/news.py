"""
News Adapter
"""

import os
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

load_dotenv()


@dataclass
class NewsItem:
    title: str
    source: str
    summary: str
    url: str
    sentiment: str


class NewsAdapter:
    """Fetches financial news."""

    BASE_URL = "https://finnhub.io/api/v1"

    SYMBOL_MAP = {
        "BTC": "BITCOIN",
        "BTC-USD": "BITCOIN",
        "ETH": "ETHEREUM",
        "ETH-USD": "ETHEREUM",
        "SOL": "SOLANA",
        "SOL-USD": "SOLANA",
        "NVDA": "NVIDIA",
    }

    def __init__(self):

        self.api_key = os.getenv("FINNHUB_API_KEY")

        if not self.api_key:
            raise ValueError(
                "FINNHUB_API_KEY not found in .env"
            )

    def latest(self, symbol: str) -> list[NewsItem]:

        keyword = self.SYMBOL_MAP.get(
            symbol.upper(),
            symbol.upper(),
        )

        try:

            response = requests.get(

                f"{self.BASE_URL}/news",

                params={
                    "category": "general",
                    "token": self.api_key,
                },

                timeout=10,

            )

            response.raise_for_status()

            articles = response.json()

        except Exception as error:

            print(error)

            return []

        news = []

        for article in articles:

            headline = article.get("headline", "")

            summary = article.get("summary", "")

            text = f"{headline} {summary}".upper()

            if keyword not in text:

                continue

            news.append(

                NewsItem(

                    title=headline,

                    source=article.get("source", ""),

                    summary=summary,

                    url=article.get("url", ""),

                    sentiment="HOLD",

                )

            )

        print(f"Found {len(news)} articles for {symbol}")

        return news