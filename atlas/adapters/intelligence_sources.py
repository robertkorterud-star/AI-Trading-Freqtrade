"""
Intelligence Sources Adapter

Aggregates external research sources for ATLAS.
"""

from dataclasses import asdict, dataclass, is_dataclass

from atlas.adapters.youtube import YouTubeAdapter
from atlas.adapters.finnhub_intelligence import (
    FinnhubIntelligenceAdapter,
)
from atlas.adapters.youtube_transcript import (
    YouTubeTranscriptAdapter,
)
from atlas.adapters.sec_research import (
    SECResearchAdapter,
)
from atlas.adapters.web_research import (
    WebResearchAdapter,
)
from atlas.adapters.direct_publisher_news import (
    DirectPublisherNewsAdapter,
)


@dataclass(slots=True)
class IntelligenceItem:
    source: str
    title: str
    summary: str
    sentiment: str


class IntelligenceSourceAdapter:
    """Aggregates and normalizes research from external sources."""

    def __init__(
        self,
        youtube=None,
        finnhub=None,
        transcript=None,
        sec=None,
        web=None,
        direct_publishers=None,
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

        self.transcript = (
            transcript
            if transcript is not None
            else YouTubeTranscriptAdapter()
        )

        self.sec = (
            sec
            if sec is not None
            else SECResearchAdapter()
        )

        self.web = web

        self.direct_publishers = (
            direct_publishers
            if direct_publishers is not None
            else DirectPublisherNewsAdapter()
        )

    @staticmethod
    def _normalize(item) -> dict:
        """Convert a source item into a standard dictionary."""

        if isinstance(item, dict):
            return item

        if is_dataclass(item):
            return asdict(item)

        return {
            "source": getattr(item, "source", ""),
            "title": getattr(item, "title", ""),
            "summary": getattr(item, "summary", ""),
            "sentiment": getattr(
                item,
                "sentiment",
                "neutral",
            ),
            "url": getattr(item, "url", ""),
            "published_at": getattr(
                item,
                "published_at",
                "",
            ),
        }

    def get(
        self,
        symbol: str,
        cik: str | None = None,
        include_sec: bool = False,
        include_transcripts: bool = True,
    ) -> list[dict]:
        """Return normalized research items from all sources."""

        results = []

        for item in self.youtube.search(symbol):

            normalized = self._normalize(item)

            video_id = normalized.get("video_id")

            if video_id and include_transcripts:
                transcript = self.transcript.get(
                    video_id
                )

                if transcript:
                    normalized["transcript"] = transcript

                    normalized["summary"] = " ".join(
                        [
                            normalized.get("summary", ""),
                            transcript,
                        ]
                    ).strip()

            results.append(normalized)

        for item in self.finnhub.search(symbol):
            results.append(self._normalize(item))

        if self.web is not None:
            for item in self.web.search(symbol):
                results.append(
                    self._normalize(item)
                )

        for item in self.direct_publishers.search(
            symbol
        ):
            results.append(
                self._normalize(item)
            )

        if include_sec or cik:
            if cik is None:
                cik = self.sec.find_cik(symbol)

            if cik:
                for item in self.sec.get_company_filings(cik):
                    results.append(self._normalize(item))

        return results
