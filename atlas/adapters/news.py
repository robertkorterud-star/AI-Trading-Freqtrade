"""
News Adapter

Fetches market-relevant news for stocks and crypto.
"""

import os
import re
from dataclasses import dataclass
from datetime import date, timedelta
from html import unescape

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
    """Fetches financial news relevant to the selected symbol."""

    BASE_URL = "https://finnhub.io/api/v1"

    CRYPTO_SYMBOLS = {
        "BTC": {
            "names": ["bitcoin", "btc"],
        },
        "BTC-USD": {
            "names": ["bitcoin", "btc"],
        },
        "ETH": {
            "names": ["ethereum", "eth"],
        },
        "ETH-USD": {
            "names": ["ethereum", "eth"],
        },
        "SOL": {
            "names": ["solana", "sol"],
        },
        "SOL-USD": {
            "names": ["solana", "sol"],
        },
    }

    POSITIVE_WORDS = (
        "surge",
        "rally",
        "growth",
        "strong",
        "record",
        "profit",
        "beats",
        "beat",
        "upgrade",
        "bullish",
        "gains",
        "gain",
        "rise",
        "rises",
        "higher",
        "buy",
        "outperform",
    )

    NEGATIVE_WORDS = (
        "fall",
        "falls",
        "drop",
        "drops",
        "loss",
        "losses",
        "lawsuit",
        "cuts",
        "cut",
        "downgrade",
        "bearish",
        "decline",
        "declines",
        "lower",
        "sell",
        "underperform",
        "warning",
    )

    def __init__(self):
        self.api_key = os.getenv("FINNHUB_API_KEY")

        if not self.api_key:
            raise ValueError(
                "FINNHUB_API_KEY not found in .env"
            )

    def latest(self, symbol: str) -> list[NewsItem]:
        """
        Return news relevant to the selected stock or cryptocurrency.

        Stocks use Finnhub company-news.
        Crypto uses Finnhub crypto news.
        """

        normalized = symbol.upper().strip()

        if normalized in self.CRYPTO_SYMBOLS:
            return self._crypto_news(normalized)

        return self._company_news(normalized)

    def _company_news(self, symbol: str) -> list[NewsItem]:
        """Fetch company-specific stock news."""

        today = date.today()
        week_ago = today - timedelta(days=7)

        try:
            response = requests.get(
                f"{self.BASE_URL}/company-news",
                params={
                    "symbol": symbol,
                    "from": week_ago.isoformat(),
                    "to": today.isoformat(),
                    "token": self.api_key,
                },
                timeout=10,
            )

            response.raise_for_status()
            articles = response.json()

        except Exception as error:
            print(
                f"News error for {symbol}: "
                f"{type(error).__name__}: {error}"
            )
            return []

        if not isinstance(articles, list):
            return []

        news = []

        for article in articles:
            headline = article.get("headline", "").strip()
            summary = self._clean_summary(article.get("summary", ""))

            if not headline:
                continue

            headline_text = headline.lower()

            # Finnhub can return loosely related market articles.
            # Only keep articles that explicitly mention the
            # selected company or ticker.
            company_keywords = {
                symbol.lower(),
            }

            if symbol == "NVDA":
                company_keywords.update(
                    {
                        "nvidia",
                        "nvidia corp",
                        "nvidia corporation",
                    }
                )

            if not any(
                keyword in headline_text
                for keyword in company_keywords
            ):
                continue

            news.append(
                NewsItem(
                    title=headline,
                    source=article.get("source", ""),
                    summary=summary,
                    url=article.get("url", ""),
                    sentiment=self._sentiment(
                        f"{headline} {summary}"
                    ),
                )
            )

        news = news[:10]

        print(
            f"Found {len(news)} relevant articles "
            f"for {symbol}"
        )

        return news

    def _crypto_news(self, symbol: str) -> list[NewsItem]:
        """Fetch crypto news and prioritize the selected asset."""

        try:
            response = requests.get(
                f"{self.BASE_URL}/news",
                params={
                    "category": "crypto",
                    "token": self.api_key,
                },
                timeout=10,
            )

            response.raise_for_status()
            articles = response.json()

        except Exception as error:
            print(
                f"Crypto news error for {symbol}: "
                f"{type(error).__name__}: {error}"
            )
            return []

        if not isinstance(articles, list):
            return []

        keywords = self.CRYPTO_SYMBOLS[symbol]["names"]

        relevant = []

        for article in articles:
            headline = article.get("headline", "").strip()
            summary = self._clean_summary(article.get("summary", ""))

            if not headline:
                continue

            # For asset-specific dashboard news, the headline
            # must explicitly mention the selected cryptocurrency.
            # Do not let a mention buried in the summary make an
            # unrelated Bitcoin/Ethereum/Solana article relevant.
            headline_text = headline.lower()

            item = NewsItem(
                title=headline,
                source=article.get("source", ""),
                summary=summary,
                url=article.get("url", ""),
                sentiment=self._sentiment(f"{headline} {summary}"),
            )

            if any(
                keyword in headline_text
                for keyword in keywords
            ):
                relevant.append(item)

        # Only return articles that explicitly mention the
        # selected cryptocurrency. Do not fill the list with
        # news about other crypto assets.
        news = relevant[:10]

        print(
            f"Found {len(relevant)} relevant articles "
            f"for {symbol}; returning {len(news)} "
            f"asset-specific crypto articles"
        )

        return news

    @staticmethod
    def _clean_summary(summary: str) -> str:
        """Clean HTML and URL-only summaries from news providers."""

        summary = unescape(summary or "").strip()

        # Some providers return HTML inside the summary.
        summary = re.sub(r"<[^>]+>", " ", summary)

        # Normalize whitespace after removing HTML.
        summary = re.sub(r"\\s+", " ", summary).strip()

        # Some providers use the article URL itself as the summary.
        if re.fullmatch(r"https?://\\S+", summary):
            return ""

        return summary

    def _sentiment(self, text: str) -> str:
        """Simple market sentiment classification."""

        lower = text.lower()

        positive = sum(
            1
            for word in self.POSITIVE_WORDS
            if word in lower
        )

        negative = sum(
            1
            for word in self.NEGATIVE_WORDS
            if word in lower
        )

        if positive > negative:
            return "BUY"

        if negative > positive:
            return "SELL"

        return "HOLD"
