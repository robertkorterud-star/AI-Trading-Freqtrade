"""Research context construction for ATLAS candidate discovery."""

from __future__ import annotations

from dataclasses import dataclass

from atlas.news.source_manager import NewsSourceManager


@dataclass(slots=True, frozen=True)
class CandidateResearchContext:
    """Bounded market research supplied to candidate discovery."""

    articles: tuple[dict, ...]

    def as_text(self, max_articles: int = 30) -> str:
        """Render research as bounded text for an AI provider."""

        lines = []

        for article in self.articles[:max_articles]:
            title = article.get("title", "")
            source = article.get("source", "")
            published_at = article.get("published_at", "")
            summary = article.get("summary", "")

            lines.append(
                f"SOURCE: {source}\n"
                f"PUBLISHED: {published_at}\n"
                f"TITLE: {title}\n"
                f"SUMMARY: {summary[:1500]}"
            )

        return "\n\n".join(lines)


class CandidateResearchContextBuilder:
    """Build candidate research from the existing news policy."""

    def __init__(
        self,
        news_source_manager: NewsSourceManager | None = None,
    ):
        self.news_source_manager = (
            news_source_manager or NewsSourceManager()
        )

    def build(self, limit: int = 50) -> CandidateResearchContext:
        articles = self.news_source_manager.market_research(
            limit=limit,
        )

        return CandidateResearchContext(
            articles=tuple(articles),
        )
