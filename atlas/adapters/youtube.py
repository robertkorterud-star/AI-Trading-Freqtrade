"""
YouTube Adapter

Searches YouTube for recent videos related to a market symbol.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()


class YouTubeAdapter:
    """Fetches YouTube research results."""

    BASE_URL = "https://www.googleapis.com/youtube/v3/search"

    def __init__(self) -> None:
        self.api_key = os.getenv("YOUTUBE_API_KEY")

    def search(self, symbol: str) -> list[dict]:
        """Search YouTube for videos related to a symbol."""

        if not self.api_key:
            return []

        try:
            response = requests.get(
                self.BASE_URL,
                params={
                    "part": "snippet",
                    "q": f"{symbol} stock crypto analysis",
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
            return []

        results = []

        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId")

            if not video_id:
                continue

            results.append(
                {
                    "source": "YouTube",
                    "title": snippet.get("title", ""),
                    "summary": snippet.get(
                        "description",
                        "",
                    ),
                    "sentiment": "neutral",
                    "url": (
                        "https://www.youtube.com/watch?v="
                        f"{video_id}"
                    ),
                    "published_at": snippet.get(
                        "publishedAt",
                        "",
                    ),
                }
            )

        return results
