"""
ATLAS Candidate Selection Report.

Provides a structured, explainable representation of why
a candidate was selected.

Research-only.
This component does not create or alter trade decisions.
"""

from dataclasses import dataclass

from atlas.market.candidate_ranking_evidence import (
    CandidateRankingEvidence,
)


@dataclass(frozen=True, slots=True)
class CandidateSelectionReport:
    """Explain why a candidate was selected."""

    symbol: str
    action: str
    ranking_evidence: CandidateRankingEvidence

    @property
    def reasoning(self) -> list[str]:
        """Return a human-readable selection report."""

        evidence = self.ranking_evidence

        result = [
            f"Selected candidate: {self.symbol}.",
            f"Action: {self.action}.",
            f"Base ranking score: {evidence.base_score:.4f}.",
            f"Regime fit score: {evidence.regime_fit:.4f}.",
            f"Final ranking score: {evidence.final_score:.4f}.",
        ]

        if evidence.regime:
            result.append(
                f"Market regime: {evidence.regime}."
            )

        if evidence.strategy:
            result.append(
                f"Strategy-memory recommendation: "
                f"{evidence.strategy}."
            )

        if evidence.regime_confidence:
            result.append(
                f"Regime-memory confidence: "
                f"{evidence.regime_confidence:.1f}/100."
            )

        if evidence.independent_run_count:
            result.append(
                f"Independent regime-memory runs: "
                f"{evidence.independent_run_count}."
            )

        if evidence.robust_winner:
            result.append(
                "Regime-memory recommendation is a "
                "robust historical winner."
            )

        return result
