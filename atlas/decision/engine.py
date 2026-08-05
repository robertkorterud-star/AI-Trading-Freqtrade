"""
Decision Engine
"""

from atlas.decision.aggregator import EvidenceAggregator
from atlas.decision.policies import (
    BUY_THRESHOLD,
    HOLD_THRESHOLD,
)

from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult
from atlas.models.decision_result import DecisionResult


class DecisionEngine:
    """Creates the final investment decision."""

    def __init__(self):

        self.aggregator = EvidenceAggregator()

    def evaluate(
        self,
        results: list[AnalysisResult],
    ) -> DecisionResult:

        if not results:
            raise ValueError("No analysis results provided.")

        summary = self.aggregator.summarize(results)

        if summary["evidence"] >= BUY_THRESHOLD:

            action = Action.BUY

        elif summary["evidence"] >= HOLD_THRESHOLD:

            action = Action.HOLD

        else:

            action = Action.SELL

        return DecisionResult(
            symbol=results[0].symbol,
            action=action,
            confidence=summary["confidence"],
            evidence=summary["evidence"],
            analysts=[r.analyst for r in results],
            reasoning=[
                "Decision based on combined analyst evidence."
            ],
        )