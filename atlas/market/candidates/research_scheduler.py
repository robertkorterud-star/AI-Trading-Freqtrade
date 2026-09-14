"""Cadence-controlled scheduler for candidate research."""

from __future__ import annotations

import time
from typing import Callable

from atlas.market.candidates.research_service import CandidateResearchService
from atlas.market.candidates.research_context import CandidateResearchContext


class CandidateResearchScheduler:
    """Schedule when CandidateResearchService should run based on time intervals."""

    DEFAULT_RESEARCH_INTERVAL_SECONDS = 10 * 60

    def __init__(
        self,
        service: CandidateResearchService | None = None,
        clock: Callable[[], float] | None = None,
        research_interval_seconds: float | None = None,
    ) -> None:
        self.service = service or CandidateResearchService()
        self._clock = clock or time.monotonic
        self.research_interval_seconds = (
            research_interval_seconds
            if research_interval_seconds is not None
            else self.DEFAULT_RESEARCH_INTERVAL_SECONDS
        )
        self._last_research_at: float | None = None
        self._last_context: CandidateResearchContext | None = None

    def should_research(self) -> bool:
        """Check if research should run, without performing it or updating state."""

        if self._last_research_at is None:
            return True

        now = self._clock()
        return now - self._last_research_at >= self.research_interval_seconds

    def research(self, limit: int = 50) -> CandidateResearchContext | None:
        """Run research and record successful completion time."""

        try:
            context = self.service.get_context(limit=limit)
            self._last_research_at = self._clock()
            self._last_context = context
            return context
        except Exception:
            return None
