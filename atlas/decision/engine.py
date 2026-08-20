"""
Decision Engine
"""

from atlas.decision.aggregator import EvidenceAggregator
from atlas.decision.intelligence_layer import IntelligenceLayer
from atlas.decision.policy import determine_action
from atlas.models.analysis_result import AnalysisResult
from atlas.models.action import Action
from atlas.trading.agent_weight_engine import AgentWeightEngine
from atlas.models.decision_result import DecisionResult


class DecisionEngine:
    """Creates the final investment decision."""

    def __init__(self):

        self.aggregator = EvidenceAggregator()
        self.intelligence = IntelligenceLayer()
        self.agent_weight_engine = None

    def evaluate(
        self,
        results: list[AnalysisResult],
    ) -> DecisionResult:

        if not results:
            raise ValueError("No analysis results provided.")

        weights = None

        if self.agent_weight_engine is not None:
            weights = self.agent_weight_engine.calculate()

        summary = self.aggregator.summarize(
            results,
            weights=weights,
        )

        intelligence = self.intelligence.summarize(
            results,
            weights=weights,
        )

        action = determine_action(
            evidence=summary["evidence"],
            agreement=intelligence.agreement,
            conflict=intelligence.conflict,
            buy_count=intelligence.buy_count,
            hold_count=intelligence.hold_count,
            sell_count=intelligence.sell_count,
        )

        # Adaptive weights may override a normal conflict only
        # when one weighted signal is clearly dominant.
        if weights:
            weighted_buy = intelligence.weighted_buy
            weighted_hold = intelligence.weighted_hold
            weighted_sell = intelligence.weighted_sell

            weighted_agreement = (
                intelligence.weighted_agreement
            )

            if (
                weighted_agreement >= 80.0
                and summary["evidence"] >= 80.0
            ):
                if (
                    weighted_buy
                    == weighted_agreement
                    and weighted_buy > weighted_sell
                    and weighted_buy > weighted_hold
                ):
                    action = Action.BUY

                elif (
                    weighted_sell
                    == weighted_agreement
                    and weighted_sell > weighted_buy
                    and weighted_sell > weighted_hold
                    and summary["evidence"] < 60.0
                ):
                    action = Action.SELL

        reasoning = [
            "Decision based on combined analyst evidence.",
            f"Overall evidence: {summary['evidence']:.1f}/100.",
            f"Overall confidence: {summary['confidence']:.1f}/100.",
            f"Analyst agreement: {intelligence.agreement:.1f}%.",
        ]

        dominant_action = None
        dominant_weight = 0.0
        opposing_analysts = []
        adaptive_override = False
        decision_margin = 0.0
        robustness = 0.0

        if weights:
            weighted_signals = {
                Action.BUY: intelligence.weighted_buy,
                Action.HOLD: intelligence.weighted_hold,
                Action.SELL: intelligence.weighted_sell,
            }

            ranked_signals = sorted(
                weighted_signals.items(),
                key=lambda item: item[1],
                reverse=True,
            )

            dominant_action = ranked_signals[0][0]
            dominant_weight = ranked_signals[0][1]

            second_weight = (
                ranked_signals[1][1]
                if len(ranked_signals) > 1
                else 0.0
            )

            decision_margin = (
                dominant_weight - second_weight
            )

            opposing_analysts = [
                result.analyst
                for result in results
                if result.action != dominant_action
            ]

            adaptive_override = (
                intelligence.weighted_conflict
                and action == dominant_action
            )

            robustness = min(
                100.0,
                (
                    decision_margin
                    * 0.7
                    + summary["evidence"]
                    * 0.3
                ),
            )

            reasoning.append(
                f"Dominant signal: "
                f"{dominant_action.value} with "
                f"{dominant_weight:.1f}% weighted influence."
            )

            if opposing_analysts:
                reasoning.append(
                    "Opposing analysts: "
                    + ", ".join(opposing_analysts)
                    + "."
                )

            reasoning.append(
                f"Adaptive weighting: "
                f"{dominant_action.value} has "
                f"{dominant_weight:.1f}% weighted influence."
            )

            if adaptive_override:
                reasoning.append(
                    "Adaptive weighting allowed the dominant "
                    "signal to overcome the opposing analyst signals."
                )

        if intelligence.conflict:
            reasoning.append(
                "Decision downgraded to HOLD because "
                "analyst signals conflict."
            )

        for analyst in summary.get("analyst_breakdown", []):
            reasoning.append(
                f"{analyst['analyst']}: {analyst['action']} "
                f"(evidence {analyst['evidence']:.1f}, "
                f"confidence {analyst['confidence']:.1f})."
            )

            for detail in analyst.get("reasoning", []):
                reasoning.append(f"  {detail}")

        return DecisionResult(
            symbol=results[0].symbol,
            action=action,
            confidence=summary["confidence"],
            evidence=summary["evidence"],
            analysts=[r.analyst for r in results],
            agent_weights=weights or {},
            dominant_action=dominant_action,
            dominant_weight=dominant_weight,
            opposing_analysts=opposing_analysts,
            adaptive_override=adaptive_override,
            decision_margin=decision_margin,
            robustness=robustness,
            reasoning=reasoning,
        )
