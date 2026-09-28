"""Structured market-research ticker candidate source."""

from __future__ import annotations

from atlas.market.candidates.source import Candidate


class ResearchTickerSource:
    """Convert related-ticker research evidence into candidates."""

    def __init__(self, articles) -> None:
        self.articles = articles or ()

    @staticmethod
    def _score(relevance_score) -> float:
        try:
            relevance = float(relevance_score)
        except (TypeError, ValueError):
            relevance = 0.0

        return max(0.0, min(100.0, relevance * 100.0))

    def discover(self) -> list[Candidate]:
        candidates = []

        for article in self.articles:
            if not isinstance(article, dict):
                continue

            related_tickers = article.get("related_tickers", [])
            if not isinstance(related_tickers, list):
                continue

            for ticker in related_tickers:
                if not isinstance(ticker, dict):
                    continue

                symbol = str(ticker.get("symbol", "")).strip().upper()
                if not symbol:
                    continue

                metadata = {
                    "relevance_score": ticker.get("relevance_score", 0.0),
                    "sentiment_score": ticker.get("sentiment_score", 0.0),
                    "sentiment": ticker.get("sentiment", "neutral"),
                }

                candidates.append(
                    Candidate(
                        symbol=symbol,
                        source="research_ticker",
                        score=self._score(
                            ticker.get("relevance_score", 0.0)
                        ),
                        reason="Related ticker from market research",
                        metadata=metadata,
                    )
                )

        return candidates
