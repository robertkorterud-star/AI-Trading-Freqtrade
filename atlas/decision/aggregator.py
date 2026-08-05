"""
Evidence Aggregator

Combines analysis results from multiple analysts.
"""

from atlas.models.analysis_result import AnalysisResult


class EvidenceAggregator:
    """Aggregates evidence from all analysts."""

    def aggregate(self, results: list[AnalysisResult]) -> dict:
        if not results:
            return {
                "evidence": 0.0,
                "confidence": 0.0,
                "analysts": [],
            }

        evidence = sum(r.evidence for r in results) / len(results)
        confidence = sum(r.confidence for r in results) / len(results)

        analysts = [r.analyst for r in results]

        return {
            "evidence": round(evidence, 2),
            "confidence": round(confidence, 2),
            "analysts": analysts,
        }