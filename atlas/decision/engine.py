"""
Decision Engine
"""

from atlas.decision.aggregator import EvidenceAggregator
from atlas.decision.intelligence_layer import IntelligenceLayer
from atlas.decision.policy import determine_action
from atlas.models.analysis_result import AnalysisResult
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
            results
        )

        action = determine_action(
            evidence=summary["evidence"],
            agreement=intelligence.agreement,
            conflict=intelligence.conflict,
            buy_count=intelligence.buy_count,
            hold_count=intelligence.hold_count,
            sell_count=intelligence.sell_count,
        )

        reasoning = [
            "Decision based on combined analyst evidence.",
            f"Overall evidence: {summary['evidence']:.1f}/100.",
            f"Overall confidence: {summary['confidence']:.1f}/100.",
            f"Analyst agreement: {intelligence.agreement:.1f}%.",
        ]

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
            reasoning=reasoning,
        )
