"""
Intelligence Sources Adapter

Aggregates external research sources for ATLAS.
"""

from dataclasses import dataclass

from atlas.adapters.youtube import YouTubeAdapter
from atlas.adapters.finnhub_intelligence import (
    FinnhubIntelligenceAdapter,
)


@dataclass(slots=True)
class IntelligenceItem:
    source: str
    title: str
    summary: str
    sentiment: str


class IntelligenceSourceAdapter:
    """Aggregates research from external sources."""

    def __init__(
        self,
        youtube=None,
        finnhub=None,
    ) -> None:

        self.youtube = (
            youtube
            if youtube is not None
            else YouTubeAdapter()
        )

        self.finnhub = (
            finnhub
            if finnhub is not None
            else FinnhubIntelligenceAdapter()
        )

    def get(self, symbol: str) -> list[dict]:
        """Return research items from all available sources."""

        results = []

        results.extend(
            self.youtube.search(symbol)
        )

        results.extend(
            self.finnhub.search(symbol)
        )

        return results
