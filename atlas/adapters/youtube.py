"""
YouTube Adapter

Searches YouTube for trading and investment research
related to a market symbol.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()


class YouTubeAdapter:
    """Fetches and ranks YouTube research results."""

    BASE_URL = (
        "https://www.googleapis.com/youtube/v3/search"
    )

    RESEARCH_QUERIES = [
        "{symbol} trading strategy",
        "{symbol} technical analysis",
        "{symbol} professional trader",
        "{symbol} momentum strategy",
        "{symbol} RSI strategy",
        "{symbol} moving average strategy",
        "{symbol} options strategy",
        "{symbol} hedge fund",
        "{symbol} institutional investor",
        "{symbol} Warren Buffett",
        "{symbol} Michael Burry",
        "{symbol} Stanley Druckenmiller",
    ]

    MAX_RESULTS = 30

    def __init__(self) -> None:
        self.api_key = os.getenv("YOUTUBE_API_KEY")

    @staticmethod
    def _score_result(item: dict, symbol: str) -> int:
        """Score a YouTube result for research relevance."""

        title = item.get("title", "").lower()
        summary = item.get("summary", "").lower()
        channel = item.get("channel", "").lower()

        text = " ".join(
            [
                title,
                summary,
                channel,
            ]
        )

        score = 0

        # The requested symbol must be relevant to the video.
        symbol_lower = symbol.lower()

        symbol_mentions = (
            text.count(symbol_lower)
        )

        if symbol_mentions == 0:
            score -= 15
        elif symbol_mentions >= 2:
            score += 4
        else:
            score += 2

        # Detect obvious references to other stocks.
        other_symbols = [
            "tsla",
            "aapl",
            "msft",
            "goog",
            "googl",
            "amzn",
            "meta",
            "amd",
            "pltr",
            "mu",
            "mstr",
            "spy",
            "qqq",
        ]

        for other_symbol in other_symbols:
            if other_symbol == symbol_lower:
                continue

            if other_symbol in text:
                score -= 2

        # Strong strategy signals.
        strong_keywords = [
            "trading strategy",
            "strategy",
            "technical analysis",
            "day trading",
            "swing trading",
            "price action",
            "risk management",
        ]

        for keyword in strong_keywords:
            if keyword in text:
                score += 5

        # Technical indicator signals.
        technical_keywords = [
            "rsi",
            "moving average",
            "ma20",
            "ma50",
            "macd",
            "support",
            "resistance",
            "momentum",
            "breakout",
            "oversold",
            "overbought",
        ]

        for keyword in technical_keywords:
            if keyword in text:
                score += 2

        # Professional/institutional signals.
        professional_keywords = [
            "professional trader",
            "professional trading",
            "hedge fund",
            "institutional",
            "institutional investor",
            "portfolio manager",
            "fund manager",
            "quant",
            "quantitative",
        ]

        for keyword in professional_keywords:
            if keyword in text:
                score += 4

        # Known investors/traders.
        expert_names = [
            "warren buffett",
            "michael burry",
            "stanley druckenmiller",
            "ray dalio",
            "paul tudor jones",
            "cathie wood",
            "peter lynch",
        ]

        for name in expert_names:
            if name in text:
                score += 3

        # Prefer actual videos with useful descriptions.
        if len(summary) > 100:
            score += 1

        # Shorts are generally less useful for strategy extraction.
        if "#shorts" in text or "shorts" in title:
            score -= 3

        return score

    def search(self, symbol: str) -> list[dict]:
        """Search YouTube and return ranked research results."""

        if not self.api_key:
            return []

        results = []
        seen_video_ids = set()

        for query_template in self.RESEARCH_QUERIES:

            query = query_template.format(
                symbol=symbol
            )

            try:
                response = requests.get(
                    self.BASE_URL,
                    params={
                        "part": "snippet",
                        "q": query,
                        "type": "video",
                        "order": "date",
                        "maxResults": 10,
                        "key": self.api_key,
                    },
                    timeout=10,
                )

                response.raise_for_status()
                data = response.json()

            except Exception:
                continue

            for item in data.get("items", []):

                snippet = item.get(
                    "snippet",
                    {},
                )

                video_id = item.get(
                    "id",
                    {},
                ).get("videoId")

                if not video_id:
                    continue

                if video_id in seen_video_ids:
                    continue

                seen_video_ids.add(video_id)

                result = {
                    "source": "YouTube",
                    "video_id": video_id,
                    "title": snippet.get(
                        "title",
                        "",
                    ),
                    "summary": snippet.get(
                        "description",
                        "",
                    ),
                    "sentiment": "neutral",
                    "channel": snippet.get(
                        "channelTitle",
                        "",
                    ),
                    "url": (
                        "https://www.youtube.com/watch?v="
                        f"{video_id}"
                    ),
                    "published_at": snippet.get(
                        "publishedAt",
                        "",
                    ),
                    "research_query": query,
                }

                result["research_score"] = (
                    self._score_result(result, symbol)
                )

                results.append(result)

        results.sort(
            key=lambda item: item["research_score"],
            reverse=True,
        )

        return results[: self.MAX_RESULTS]
