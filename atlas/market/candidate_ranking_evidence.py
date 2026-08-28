"""
ATLAS Candidate Ranking Evidence.

Provides an explainable representation of how a candidate
received its ranking score.

Research-only.
This component does not create or alter trade decisions.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CandidateRankingEvidence:
    """Explain the components of a candidate ranking."""

    symbol: str
    base_score: float
    regime_fit: float
    final_score: float
    regime: str | None = None
    strategy: str | None = None
    regime_confidence: float = 0.0
    independent_run_count: int = 0
    robust_winner: bool = False

    @property
    def reasoning(self) -> list[str]:
        """Return human-readable ranking explanations."""

        result = [
            f"Base ranking score: {self.base_score:.4f}.",
            f"Regime fit score: {self.regime_fit:.4f}.",
            f"Final ranking score: {self.final_score:.4f}.",
        ]

        if self.regime:
            result.append(
                f"Market regime: {self.regime}."
            )

        if self.strategy:
            result.append(
                f"Strategy-memory recommendation: "
                f"{self.strategy}."
            )

        if self.regime_confidence:
            result.append(
                f"Regime-memory confidence: "
                f"{self.regime_confidence:.1f}/100."
            )

        if self.independent_run_count:
            result.append(
                f"Independent regime-memory runs: "
                f"{self.independent_run_count}."
            )

        if self.robust_winner:
            result.append(
                "Regime-memory recommendation is a "
                "robust historical winner."
            )

        return result
