"""AI-research candidate source for ATLAS."""

from typing import Protocol

from atlas.market.candidates.source import Candidate


class AIResearchProvider(Protocol):
    """Provider capable of proposing candidates through research."""

    def discover_candidates(self) -> list[Candidate]:
        """Return candidates identified through AI research."""
        ...


class AIResearchSource:
    """Expose AI research as the CandidateSource contract."""

    def __init__(self, provider: AIResearchProvider):
        self.provider = provider

    def discover(self) -> list[Candidate]:
        """Return candidates proposed by the configured research provider."""

        return [
            candidate
            for candidate in self.provider.discover_candidates()
            if candidate.symbol.strip()
        ]
