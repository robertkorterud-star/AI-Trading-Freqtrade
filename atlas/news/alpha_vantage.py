"""Alpha Vantage NEWS_SENTIMENT source for ATLAS news collection."""

import os

import requests
from dotenv import load_dotenv


load_dotenv()


class AlphaVantageNewsAdapter:
    """Fetch normalized, symbol-relevant news from Alpha Vantage."""

    BASE_URL = "https://www.alphavantage.co/query"

    SYMBOL_MAP = {
        "AAPL": "AAPL",
        "NVDA": "NVDA",
        "BTC-USD": "CRYPTO:BTC",
        "ETH-USD": "CRYPTO:ETH",
        "SOL-USD": "CRYPTO:SOL",
        "XRP-USD": "CRYPTO:XRP",
    }

    def __init__(self) -> None:
        self.api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

    @classmethod
    def ticker_for_symbol(cls, symbol: str) -> str | None:
        """Map an ATLAS symbol to Alpha Vantage's NEWS_SENTIMENT ticker."""

        normalized = (symbol or "").strip().upper()
        return cls.SYMBOL_MAP.get(normalized)

    def search(self, symbol: str) -> list[dict]:
        """Return normalized Alpha Vantage news, or no items when unavailable."""

        ticker = self.ticker_for_symbol(symbol)
        if not self.api_key or ticker is None:
            return []

        try:
            response = requests.get(
                self.BASE_URL,
                params={
                    "function": "NEWS_SENTIMENT",
                    "tickers": ticker,
                    "apikey": self.api_key,
                },
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return []

        feed = payload.get("feed", [])
        if not isinstance(feed, list):
            return []

        results = []
        for article in feed:
            title = str(article.get("title", "")).strip()
            if not title:
                continue

            sentiment = str(
                article.get("overall_sentiment_label", "neutral")
            ).strip().lower()
            sentiment = {
                "bullish": "positive",
                "somewhat-bullish": "positive",
                "positive": "positive",
                "bearish": "negative",
                "somewhat-bearish": "negative",
                "negative": "negative",
            }.get(sentiment, "neutral")

            results.append(
                {
                    "title": title,
                    "source": str(article.get("source", "Alpha Vantage")).strip()
                    or "Alpha Vantage",
                    "summary": str(article.get("summary", "")).strip(),
                    "url": str(article.get("url", "")).strip(),
                    "sentiment": sentiment,
                    "published_at": str(
                        article.get("time_published", "")
                    ).strip(),
                }
            )

        return results
