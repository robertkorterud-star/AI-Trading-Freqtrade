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
        self.last_intelligence = None

    def _strongest_action_support(
        self,
        action: Action,
    ):
        """Return strongest learned support for an action."""

        if self.agent_weight_engine is None:
            return None

        try:
            weights = self.agent_weight_engine.calculate(
                action=action.value,
            )
        except TypeError:
            # Preserve compatibility with simpler weight-engine
            # implementations that only expose calculate().
            weights = self.agent_weight_engine.calculate()

        if not weights:
            return None

        analyst, weight = max(
            weights.items(),
            key=lambda item: item[1],
        )

        return {
            "analyst": analyst,
            "weight": weight,
            "action": action.value,
        }

    def _strongest_learned_action_support(self):
        """Return the strongest learned directional support."""

        if self.agent_weight_engine is None:
            return None

        supports = []

        for action in (
            Action.BUY,
            Action.SELL,
        ):
            support = self._strongest_action_support(
                action,
            )

            if support is not None:
                supports.append(support)

        if not supports:
            return None

        return max(
            supports,
            key=lambda item: item["weight"],
        )

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

        self.last_intelligence = intelligence

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

        initial_dominant_action = dominant_action

        action_support = (
            self._strongest_learned_action_support()
        )

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

        unanimous = (
            intelligence.buy_count == len(results)
            or intelligence.hold_count == len(results)
            or intelligence.sell_count == len(results)
        )

        policy_action = determine_action(
            evidence=summary["evidence"],
            agreement=intelligence.agreement,
            conflict=intelligence.conflict,
            buy_count=intelligence.buy_count,
            hold_count=intelligence.hold_count,
            sell_count=intelligence.sell_count,
        )

        action = policy_action
        adaptive_override = False

        # A unanimous analyst decision must never be reversed
        # by an unrelated policy threshold.
        if unanimous:
            action = dominant_action

        # Adaptive learning may resolve a genuine BUY/SELL
        # conflict when the learned dominant signal is strong
        # enough in both weight and underlying evidence.
        #
        # MAX_WEIGHT is intentionally capped at 60%, so the
        # override threshold must never require an impossible
        # weight above that safety limit.
        elif (
            weights
            and intelligence.weighted_conflict
            and dominant_action in {
                Action.BUY,
                Action.SELL,
            }
            and dominant_weight >= 60.0
            and decision_margin >= 20.0
            and summary["evidence"] >= 80.0
        ):
            action = dominant_action
            adaptive_override = True

        raw_robustness = (
            decision_margin * 0.7
            + summary["evidence"] * 0.3
        )

        # Evidence is the ceiling for robustness when the
        # underlying evidence is weak. Strong agreement alone
        # must not manufacture a strong decision.
        robustness = min(
            100.0,
            raw_robustness,
            summary["evidence"],
        )

        # Evidence limits the robustness classification.
        # Agreement alone must never create a STRONG decision.
        if summary["evidence"] < 60.0:
            robustness_level = "WEAK"
        elif summary["evidence"] < 80.0:
            robustness_level = (
                "MODERATE"
                if robustness >= 60.0
                else "WEAK"
            )
        elif robustness >= 80.0:
            robustness_level = "STRONG"
        elif robustness >= 60.0:
            robustness_level = "MODERATE"
        else:
            robustness_level = "WEAK"

        reasoning = [
            "Decision based on combined analyst evidence.",
            f"Overall evidence: {summary['evidence']:.1f}/100.",
            f"Overall confidence: {summary['confidence']:.1f}/100.",
            f"Analyst agreement: {intelligence.agreement:.1f}%.",
        ]

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

        if weights:
            reasoning.append(
                f"Adaptive weighting: "
                f"{dominant_action.value} has "
                f"{dominant_weight:.1f}% weighted influence."
            )

        if action_support:
            reasoning.append(
                f"Learned support: "
                f"{action_support['analyst']} supports "
                f"{action_support['action']} with "
                f"{action_support['weight'] * 100:.1f}% learned weight."
            )

        if adaptive_override:
            reasoning.append(
                "Adaptive weighting allowed the dominant "
                "signal to overcome the opposing analyst signals."
            )

        if intelligence.conflict and not adaptive_override:
            reasoning.append(
                "Decision held because analyst signals conflict."
            )

        for analyst in summary.get("analyst_breakdown", []):
            reasoning.append(
                f"{analyst['analyst']}: {analyst['action']} "
                f"(evidence {analyst['evidence']:.1f}, "
                f"confidence {analyst['confidence']:.1f})."
            )

            for detail in analyst.get("reasoning", []):
                reasoning.append(
                    f"  {detail}"
                )

        reasoning.append(
            f"Decision robustness: "
            f"{robustness:.1f}% ({robustness_level})."
        )

        return DecisionResult(
            symbol=results[0].symbol,
            action=action,
            confidence=summary["confidence"],
            evidence=summary["evidence"],
            analysts=[r.analyst for r in results],
            agent_weights=weights or {},
            dominant_action=dominant_action,
            dominant_weight=dominant_weight,
            action_support_analyst=(
                action_support["analyst"]
                if action_support
                else None
            ),
            action_support_action=(
                Action(action_support["action"])
                if action_support
                else None
            ),
            action_support_weight=(
                action_support["weight"]
                if action_support
                else 0.0
            ),
            opposing_analysts=opposing_analysts,
            adaptive_override=adaptive_override,
            decision_margin=decision_margin,
            robustness=robustness,
            robustness_level=robustness_level,
            reasoning=reasoning,
        )

