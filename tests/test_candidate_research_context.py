from atlas.market.candidates.research_context import (
    CandidateResearchContext,
    CandidateResearchContextBuilder,
)


class FakeNewsSourceManager:
    def market_research(self, limit=50):
        return [
            {
                "source": "Reuters",
                "published_at": "2026-09-14T10:00:00",
                "title": "Nvidia demand accelerates",
                "summary": "Strong semiconductor demand.",
            },
            {
                "source": "Alpha Vantage",
                "published_at": "2026-09-14T09:00:00",
                "title": "Bitcoin sentiment improves",
                "summary": "Crypto market sentiment is improving.",
            },
        ]


def test_candidate_research_context_builder():
    context = CandidateResearchContextBuilder(
        FakeNewsSourceManager()
    ).build()

    assert len(context.articles) == 2
    assert "Nvidia demand accelerates" in context.as_text()
    assert "Bitcoin sentiment improves" in context.as_text()


def test_candidate_research_context_is_bounded():
    context = CandidateResearchContext(
        articles=tuple(
            {
                "source": "Test",
                "published_at": "",
                "title": f"Headline {index}",
                "summary": "x" * 3000,
            }
            for index in range(50)
        )
    )

    rendered = context.as_text(max_articles=3)

    assert "Headline 0" in rendered
    assert "Headline 2" in rendered
    assert "Headline 3" not in rendered
    assert len(rendered) < 10000


def test_candidate_research_context_preserves_normalized_news_evidence():
    context = CandidateResearchContext(
        articles=(
            {
                "source": "Reuters",
                "published_at": "2026-09-14T10:00:00",
                "title": "Nvidia demand accelerates",
                "summary": "Strong semiconductor demand.",
                "url": "https://example.com/nvda",
                "sentiment": "positive",
            },
        )
    )

    rendered = context.as_text()

    assert "SOURCE: Reuters" in rendered
    assert "PUBLISHED: 2026-09-14T10:00:00" in rendered
    assert "TITLE: Nvidia demand accelerates" in rendered
    assert "SUMMARY: Strong semiconductor demand." in rendered
    assert "URL: https://example.com/nvda" in rendered
    assert "SENTIMENT: positive" in rendered

def test_candidate_research_context_exposes_related_tickers():
    context = CandidateResearchContext(
        articles=(
            {
                "source": "Alpha Vantage",
                "published_at": "2026-09-28T10:00:00",
                "title": "Chip demand accelerates",
                "summary": "Semiconductor shares react.",
                "related_tickers": [
                    {
                        "symbol": "AMD",
                        "relevance_score": 0.91,
                        "sentiment_score": 0.42,
                        "sentiment": "positive",
                    },
                    {
                        "symbol": "NVDA",
                        "relevance_score": 0.84,
                        "sentiment_score": 0.31,
                        "sentiment": "positive",
                    },
                ],
            },
        )
    )

    rendered = context.as_text()

    assert "RELATED TICKERS:" in rendered
    assert "AMD" in rendered
    assert "relevance=0.91" in rendered
    assert "NVDA" in rendered
    assert "sentiment=positive" in rendered

