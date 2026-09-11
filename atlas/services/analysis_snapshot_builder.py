"""
ATLAS Analysis Snapshot Builder

Converts live ATLAS analysis and decision objects
into a persistent AnalysisSnapshot.
"""

from datetime import datetime

from atlas.models.analysis_snapshot import AnalysisSnapshot


class AnalysisSnapshotBuilder:
    """Builds persistent snapshots from ATLAS analysis results."""

    def build(
        self,
        symbol,
        results,
        decision,
        intelligence=None,
        provider="unknown",
        model="unknown",
    ):
        return AnalysisSnapshot(
            database_id=None,
            symbol=symbol,
            timestamp=datetime.now(),
            provider=provider,
            model=model,
            results=[
                self._serialize_result(result)
                for result in results
            ],
            decision=self._serialize_decision(
                decision
            ),
            intelligence=self._build_intelligence(
                intelligence,
                results,
                decision,
            ),
            decision_ref=decision,
        )

    @staticmethod
    def _serialize_result(result):
        data = {
            "analyst": result.analyst,
            "symbol": result.symbol,
            "action": result.action.value,
            "confidence": float(result.confidence),
            "evidence": float(result.evidence),
            "reasoning": list(result.reasoning),
        }
        metadata = getattr(result, "metadata", None)
        if metadata:
            data["metadata"] = dict(metadata)
        return data

    @staticmethod
    def _serialize_decision(decision):
        return {
            "symbol": decision.symbol,
            "action": decision.action.value,
            "confidence": float(
                decision.confidence
            ),
            "evidence": float(
                decision.evidence
            ),
            "analysts": list(
                decision.analysts
            ),
            "agent_weights": dict(
                decision.agent_weights
            ),
            "dominant_action": (
                decision.dominant_action.value
                if decision.dominant_action
                else None
            ),
            "dominant_weight": float(
                decision.dominant_weight
            ),
            "action_support_analyst": (
                decision.action_support_analyst
            ),
            "action_support_action": (
                decision.action_support_action.value
                if decision.action_support_action
                else None
            ),
            "action_support_weight": float(
                decision.action_support_weight
            ),
            "opposing_analysts": list(
                decision.opposing_analysts
            ),
            "adaptive_override": bool(
                decision.adaptive_override
            ),
            "decision_margin": float(
                decision.decision_margin
            ),
            "robustness": float(
                decision.robustness
            ),
            "robustness_level": (
                decision.robustness_level
            ),
            "reasoning": list(
                decision.reasoning
            ),
        }

    @staticmethod
    def _build_intelligence(
        intelligence,
        results,
        decision,
    ):
        """Serialize IntelligenceSummary or create a test fallback."""

        if intelligence is None:
            buy_count = sum(
                1
                for result in results
                if result.action.value == "BUY"
            )

            hold_count = sum(
                1
                for result in results
                if result.action.value == "HOLD"
            )

            sell_count = sum(
                1
                for result in results
                if result.action.value == "SELL"
            )

            total = len(results)

            if total > 0:
                agreement = (
                    max(
                        buy_count,
                        hold_count,
                        sell_count,
                    )
                    / total
                ) * 100.0

                conflict = sum(
                    count > 0
                    for count in (
                        buy_count,
                        hold_count,
                        sell_count,
                    )
                ) > 1
            else:
                agreement = 0.0
                conflict = False

            return {
                "symbol": decision.symbol,
                "action": decision.action.value,
                "evidence": float(
                    decision.evidence
                ),
                "confidence": float(
                    decision.confidence
                ),
                "buy_count": buy_count,
                "hold_count": hold_count,
                "sell_count": sell_count,
                "agreement": agreement,
                "conflict": conflict,
                "weighted_buy": 0.0,
                "weighted_hold": 0.0,
                "weighted_sell": 0.0,
                "weighted_agreement": 0.0,
                "weighted_conflict": False,
                "analysts": [
                    result.analyst
                    for result in results
                ],
                "reasoning": list(
                    decision.reasoning
                ),
            }

        return {
            "symbol": intelligence.symbol,
            "action": intelligence.action.value,
            "evidence": float(
                intelligence.evidence
            ),
            "confidence": float(
                intelligence.confidence
            ),
            "buy_count": int(
                intelligence.buy_count
            ),
            "hold_count": int(
                intelligence.hold_count
            ),
            "sell_count": int(
                intelligence.sell_count
            ),
            "agreement": float(
                intelligence.agreement
            ),
            "conflict": bool(
                intelligence.conflict
            ),
            "weighted_buy": float(
                intelligence.weighted_buy
            ),
            "weighted_hold": float(
                intelligence.weighted_hold
            ),
            "weighted_sell": float(
                intelligence.weighted_sell
            ),
            "weighted_agreement": float(
                intelligence.weighted_agreement
            ),
            "weighted_conflict": bool(
                intelligence.weighted_conflict
            ),
            "analysts": list(
                intelligence.analysts
            ),
            "reasoning": list(
                intelligence.reasoning
            ),
        }
