"""
Evidence Aggregator
"""

from atlas.models.analysis_result import AnalysisResult


class EvidenceAggregator:
    """Combines multiple analyst results."""

    def summarize(self, results: list[AnalysisResult]) -> dict:

        if not results:
            return {
                "evidence": 0.0,
                "confidence": 0.0,
            }

        evidence = sum(r.evidence for r in results) / len(results)

        confidence = sum(r.confidence for r in results) / len(results)

        return {
            "evidence": evidence,
            "confidence": confidence,
        }