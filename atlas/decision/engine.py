"""
Decision Engine
"""

from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult
from atlas.models.decision_result import DecisionResult
from atlas.decision.aggregator import EvidenceAggregator


class DecisionEngine:

    def __init__(self):
        self.aggregator = EvidenceAggregator()

    def evaluate(
        self,
        results: list[AnalysisResult],
    ) -> DecisionResult:

        summary = self.aggregator.aggregate(results)

        if summary["evidence"] >= 80:
            action = Action.BUY

        elif summary["evidence"] >= 60:
            action = Action.HOLD

        else:
            action = Action.SELL

        symbol = results[0].symbol if results else "UNKNOWN"

        return DecisionResult(
            symbol=symbol,
            action=action,
            confidence=summary["confidence"],
            evidence=summary["evidence"],
            analysts=summary["analysts"],
            reasoning=["Decision based on combined analyst evidence."],
        )