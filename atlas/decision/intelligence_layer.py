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
        weights: dict[str, float] | None = None,
    ) -> IntelligenceSummary:

        if not results:
            raise ValueError(
                "No analysis results provided."
            )

        active_results = [
            result
            for result in results
            if result.confidence > 0.0 or result.evidence > 0.0
        ]

        # Fully uninformative analysis carries no directional decision weight.
        # Keep it in the original results for reporting, but do not let a
        # zero-confidence, zero-evidence result create conflict or dilute evidence.
        decision_results = active_results or results

        buy_count = sum(
            1 for result in decision_results
            if result.action == Action.BUY
        )

        hold_count = sum(
            1 for result in decision_results
            if result.action == Action.HOLD
        )

        sell_count = sum(
            1 for result in decision_results
            if result.action == Action.SELL
        )

        total = len(decision_results)

        evidence = (
            sum(result.evidence for result in decision_results)
            / total
        )

        confidence = (
            sum(result.confidence for result in decision_results)
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

        if total_weight <= 0:
            effective_weights = {
                result.analyst: 1.0
                for result in decision_results
            }

            total_weight = float(total)

        weighted_buy = (
            sum(
                effective_weights[result.analyst]
                for result in decision_results
                if result.action == Action.BUY
            )
            / total_weight
        ) * 100.0

        weighted_hold = (
            sum(
                effective_weights[result.analyst]
                for result in decision_results
                if result.action == Action.HOLD
            )
            / total_weight
        ) * 100.0

        weighted_sell = (
            sum(
                effective_weights[result.analyst]
                for result in decision_results
                if result.action == Action.SELL
            )
            / total_weight
        ) * 100.0

        weighted_agreement = max(
            weighted_buy,
            weighted_hold,
            weighted_sell,
        )

        weighted_conflict = (
            sum(
                value > 0.0
                for value in (
                    weighted_buy,
                    weighted_hold,
                    weighted_sell,
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
            weighted_buy=weighted_buy,
            weighted_hold=weighted_hold,
            weighted_sell=weighted_sell,
            weighted_agreement=weighted_agreement,
            weighted_conflict=weighted_conflict,
            analysts=[
                result.analyst
                for result in results
            ],
            reasoning=reasoning,
        )
