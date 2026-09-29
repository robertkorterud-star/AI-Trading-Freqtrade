"""Candidate source contracts for ATLAS research."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(slots=True, frozen=True)
class Candidate:
    """A research candidate proposed for deeper ATLAS analysis."""

    symbol: str
    source: str
    score: float = 0.0
    reason: str = ""
    metadata: dict = field(default_factory=dict)


class CandidateSource(Protocol):
    """Protocol implemented by candidate discovery/research sources."""

    def discover(self) -> list[Candidate]:
        """Return candidates worth considering for deeper research."""
        ...


class CandidatePool:
    """Combine candidates from multiple sources without duplicating symbols."""

    def __init__(self, sources: list[CandidateSource] | None = None):
        self.sources = sources or []

    def collect(self) -> list[Candidate]:
        """Collect candidates and merge duplicate symbols."""

        candidates: dict[str, Candidate] = {}

        for source in self.sources:
            try:
                discovered = source.discover()
            except Exception:
                continue

            for candidate in discovered:
                symbol = candidate.symbol.strip().upper()

                if not symbol:
                    continue

                normalized = Candidate(
                    symbol=symbol,
                    source=candidate.source,
                    score=float(candidate.score),
                    reason=candidate.reason,
                    metadata=dict(candidate.metadata),
                )

                existing = candidates.get(symbol)

                if existing is None:
                    candidates[symbol] = normalized
                    continue

                if normalized.score > existing.score:
                    metadata = dict(existing.metadata)
                    metadata.update(normalized.metadata)
                    candidates[symbol] = Candidate(
                        symbol=normalized.symbol,
                        source=normalized.source,
                        score=normalized.score,
                        reason=normalized.reason,
                        metadata=metadata,
                    )
                else:
                    metadata = dict(normalized.metadata)
                    metadata.update(existing.metadata)
                    candidates[symbol] = Candidate(
                        symbol=existing.symbol,
                        source=existing.source,
                        score=existing.score,
                        reason=existing.reason,
                        metadata=metadata,
                    )

        return sorted(
            candidates.values(),
            key=lambda candidate: candidate.score,
            reverse=True,
        )
