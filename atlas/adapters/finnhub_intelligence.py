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
    CRYPTO_NEWS_URL = "https://finnhub.io/api/v1/news"

    CRYPTO_SYMBOLS = {
        "BTC": ("bitcoin", "btc"),
        "BTC-USD": ("bitcoin", "btc"),
        "ETH": ("ethereum", "eth"),
        "ETH-USD": ("ethereum", "eth"),
        "SOL": ("solana", "sol"),
        "SOL-USD": ("solana", "sol"),
        "XRP": ("xrp", "ripple"),
        "XRP-USD": ("xrp", "ripple"),
    }

    def __init__(self) -> None:
        self.api_key = os.getenv("FINNHUB_API_KEY")

    def search(self, symbol: str) -> list[dict]:
        """Fetch recent company news for a symbol."""

        if not self.api_key:
            return []

        normalized_symbol = symbol.upper().strip()
        if normalized_symbol in self.CRYPTO_SYMBOLS:
            return self._crypto_news(normalized_symbol)

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

    def _crypto_news(self, symbol: str) -> list[dict]:
        """Fetch crypto news and retain only items relevant to the asset."""

        try:
            response = requests.get(
                self.CRYPTO_NEWS_URL,
                params={
                    "category": "crypto",
                    "token": self.api_key,
                },
                timeout=10,
            )
            response.raise_for_status()
            articles = response.json()
        except Exception:
            return []

        if not isinstance(articles, list):
            return []

        asset = symbol.removesuffix("-USD")
        keywords = self.CRYPTO_SYMBOLS[symbol]
        results = []

        for article in articles:
            headline = str(article.get("headline", "")).strip()
            summary = str(article.get("summary", "")).strip()
            related = article.get("related", "")
            if isinstance(related, str):
                related_symbols = {
                    value.strip().upper()
                    for value in related.replace(",", " ").split()
                    if value.strip()
                }
            elif isinstance(related, (list, tuple, set)):
                related_symbols = {
                    str(value).strip().upper()
                    for value in related
                    if str(value).strip()
                }
            else:
                related_symbols = set()

            text = f"{headline} {summary}".lower()
            if asset not in related_symbols and not any(
                keyword in text for keyword in keywords
            ):
                continue

            results.append(
                {
                    "source": "Finnhub",
                    "title": headline,
                    "summary": summary,
                    "sentiment": "neutral",
                    "url": article.get("url", ""),
                    "published_at": article.get("datetime", ""),
                }
            )

        return results
