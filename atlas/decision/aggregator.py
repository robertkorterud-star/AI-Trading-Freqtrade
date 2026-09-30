"""
Evidence Aggregator
"""

from atlas.models.analysis_result import AnalysisResult


class EvidenceAggregator:
    """Combine analyst results."""

    def summarize(
        self,
        results: list[AnalysisResult],
        weights: dict[str, float] | None = None,
    ) -> dict:

        if not results:
            return {
                "evidence": 0.0,
                "confidence": 0.0,
            }

        active_results = [
            result
            for result in results
            if result.confidence > 0.0 or result.evidence > 0.0
        ]

        # Fully uninformative analysis remains available for reporting but
        # carries no weight in aggregate decision evidence or confidence.
        decision_results = active_results or results

        if weights is None:
            weights = {}

        effective_weights = {
            result.analyst: max(
                0.0,
                float(weights.get(result.analyst, 0.0)),
            )
            for result in decision_results
        }

        total_weight = sum(
            effective_weights.values()
        )

        # Unknown or incomplete weights fall back to
        # equal weighting rather than silently discarding
        # analysts.
        if total_weight <= 0:
            effective_weights = {
                result.analyst: 1.0
                for result in decision_results
            }

            total_weight = float(len(decision_results))

        evidence = sum(
            result.evidence
            * effective_weights[result.analyst]
            for result in decision_results
        ) / total_weight

        confidence = sum(
            result.confidence
            * effective_weights[result.analyst]
            for result in decision_results
        ) / total_weight

        return {
            "evidence": evidence,
            "confidence": confidence,
            "analyst_breakdown": [
                {
                    "analyst": result.analyst,
                    "action": result.action.value,
                    "confidence": result.confidence,
                    "evidence": result.evidence,
                    "reasoning": result.reasoning,
                }
                for result in results
            ],
        }