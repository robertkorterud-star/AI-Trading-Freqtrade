"""Cadence-controlled candidate research service."""

from __future__ import annotations

import time
from typing import Callable

from atlas.market.candidates.research_context import (
    CandidateResearchContext,
    CandidateResearchContextBuilder,
)


class CandidateResearchService:
    """Return fresh candidate research context on a minimum cadence."""

    MIN_RESEARCH_INTERVAL_SECONDS = 10 * 60

    def __init__(
        self,
        context_builder: CandidateResearchContextBuilder | None = None,
        clock: Callable[[], float] | None = None,
        minimum_interval_seconds: float | None = None,
        min_interval_seconds: float | None = None,
    ) -> None:
        self.context_builder = (
            context_builder or CandidateResearchContextBuilder()
        )
        self._clock = clock or time.monotonic
        interval = (
            minimum_interval_seconds
            if minimum_interval_seconds is not None
            else min_interval_seconds
        )
        self.minimum_interval_seconds = (
            interval
            if interval is not None
            else self.MIN_RESEARCH_INTERVAL_SECONDS
        )
        self.min_interval_seconds = self.minimum_interval_seconds
        self._cached_context: CandidateResearchContext | None = None
        self._last_research_at: float | None = None
        self._last_researched_at: float | None = None

    @property
    def last_research_at(self) -> float | None:
        return self._last_research_at

    def get_context(
        self,
        limit: int = 50,
    ) -> CandidateResearchContext:
        """Return cached market-research context until the cooldown expires."""

        now = self._clock()

        last_research_at = self._last_research_at
        if last_research_at is None:
            last_research_at = self._last_researched_at

        if (
            self._cached_context is not None
            and last_research_at is not None
            and now - last_research_at < self.minimum_interval_seconds
        ):
            return self._cached_context

        context = self.context_builder.build(limit=limit)
        self._cached_context = context
        self._last_research_at = now
        self._last_researched_at = now
        return context

    def research(
        self,
        limit: int = 50,
    ) -> CandidateResearchContext:
        """Compatibility wrapper for callers that prefer the research verb."""

        return self.get_context(limit=limit)
