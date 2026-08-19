"""
ATLAS Intelligence Layer

Combines standardized analyst results into a higher-level
view of agreement, conflict, evidence and confidence.

The Intelligence Layer does not replace the Decision Engine.
"""

from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult
from atlas.models.intelligence_summary import IntelligenceSummary


class IntelligenceLayer:
    """Summarize agreement between ATLAS analysts."""

    def summarize(
        self,
        results: list[AnalysisResult],
    ) -> IntelligenceSummary:

        if not results:
            raise ValueError(
                "No analysis results provided."
            )

        buy_count = sum(
            1 for result in results
            if result.action == Action.BUY
        )

        hold_count = sum(
            1 for result in results
            if result.action == Action.HOLD
        )

        sell_count = sum(
            1 for result in results
            if result.action == Action.SELL
        )

        total = len(results)

        evidence = (
            sum(result.evidence for result in results)
            / total
        )

        confidence = (
            sum(result.confidence for result in results)
            / total
        )

        highest_count = max(
            buy_count,
            hold_count,
            sell_count,
        )

        agreement = (
            highest_count / total
        ) * 100.0

        conflict = (
            sum(
                count > 0
                for count in (
                    buy_count,
                    hold_count,
                    sell_count,
                )
            )
            > 1
        )

        if buy_count >= hold_count and buy_count >= sell_count:
            action = Action.BUY
        elif hold_count >= buy_count and hold_count >= sell_count:
            action = Action.HOLD
        else:
            action = Action.SELL

        reasoning = [
            f"{buy_count} BUY, "
            f"{hold_count} HOLD, "
            f"{sell_count} SELL signals.",
            f"Analyst agreement: {agreement:.1f}%.",
            f"Combined evidence: {evidence:.1f}/100.",
            f"Combined confidence: {confidence:.1f}/100.",
        ]

        if conflict:
            reasoning.append(
                "Analyst signals are in conflict."
            )
        else:
            reasoning.append(
                "Analysts are aligned."
            )

        return IntelligenceSummary(
            symbol=results[0].symbol,
            action=action,
            evidence=evidence,
            confidence=confidence,
            buy_count=buy_count,
            hold_count=hold_count,
            sell_count=sell_count,
            agreement=agreement,
            conflict=conflict,
            analysts=[
                result.analyst
                for result in results
            ],
            reasoning=reasoning,
        )
