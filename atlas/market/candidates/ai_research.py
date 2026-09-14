"""AI-backed candidate discovery source for ATLAS."""

from __future__ import annotations

from typing import Protocol

from atlas.market.candidates.source import Candidate


class AIResearchProvider(Protocol):
    def discover_candidates(
        self,
        research: str = "",
    ) -> list[Candidate]:
        ...


class AIResearchSource:
    """Candidate source backed by AI research."""

    def __init__(
        self,
        provider: AIResearchProvider,
        research: str = "",
    ):
        self.provider = provider
        self.research = research

    def discover(self) -> list[Candidate]:
        candidates = self.provider.discover_candidates(
            self.research
        )

        return [
            candidate
            for candidate in candidates
            if candidate.symbol.strip()
        ]
