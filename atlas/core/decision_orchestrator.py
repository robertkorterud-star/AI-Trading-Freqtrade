"""ATLAS decision orchestration layer.

Connects market intelligence, multi-horizon analysis, risk gating and
position management into one deterministic decision pipeline.

The orchestrator does not place live orders. Its output is intended for
paper/dry-run execution and for the learning layer to evaluate later.
"""

from __future__ import annotations

from dataclasses import dataclass

from atlas.agents.intelligence import IntelligenceResult
from atlas.algorithms.base import AlgorithmSignal
from atlas.algorithms.decision_core import (
    DecisionCore,
    DecisionResult,
    RiskContext,
)
from atlas.algorithms.multi_horizon import MultiHorizonResult
from atlas.algorithms.position_exit import (
    PositionContext,
    PositionDecision,
    PositionExitEngine,
)
from atlas.models.action import Action


@dataclass(frozen=True, slots=True)
class OrchestrationResult:
    """Complete decision trace produced by ATLAS."""

    symbol: str
    decision: DecisionResult
    position: PositionDecision
    combined_score: float
    combined_confidence: float
    reasoning: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "decision": {
                "action": self.decision.action.value,
                "confidence": self.decision.confidence,
                "risk_score": self.decision.risk_score,
                "score": self.decision.score,
                "reason": self.decision.reason,
            },
            "position": {
                "action": self.position.action.value,
                "target_position": self.position.target_position,
                "size_fraction": self.position.size_fraction,
                "reason": self.position.reason,
            },
            "combined_score": self.combined_score,
            "combined_confidence": self.combined_confidence,
            "reasoning": list(self.reasoning),
        }


class DecisionOrchestrator:
    """Fuse ATLAS intelligence into one paper-trading decision."""

    def __init__(
        self,
        decision_core: DecisionCore | None = None,
        position_engine: PositionExitEngine | None = None,
        intelligence_weight: float = 0.35,
        horizon_weight: float = 0.65,
    ):
        if intelligence_weight < 0.0 or horizon_weight < 0.0:
            raise ValueError("weights must be non-negative")
        if intelligence_weight + horizon_weight <= 0.0:
            raise ValueError("at least one weight must be positive")

        self.decision_core = decision_core or DecisionCore()
        self.position_engine = position_engine or PositionExitEngine()

        total = intelligence_weight + horizon_weight
        self.intelligence_weight = intelligence_weight / total
        self.horizon_weight = horizon_weight / total

    def decide(
        self,
        intelligence: IntelligenceResult,
        horizon: MultiHorizonResult,
        risk: RiskContext | None = None,
        position: PositionContext | None = None,
    ) -> OrchestrationResult:
        """Produce a complete decision without executing an order."""

        if intelligence.symbol != horizon.symbol:
            raise ValueError("intelligence and horizon symbols must match")

        intelligence_score = self._clamp_signed(intelligence.score)
        horizon_score = self._horizon_score(horizon)

        combined_score = (
            intelligence_score * self.intelligence_weight
            + horizon_score * self.horizon_weight
        )

        intelligence_confidence = self._clamp(intelligence.confidence)
        horizon_confidence = self._normalise_horizon_confidence(
            horizon.confidence
        )
        combined_confidence = (
            intelligence_confidence * self.intelligence_weight
            + horizon_confidence * self.horizon_weight
        )

        composite_action = self._action_from_score(combined_score)
        composite_signal = AlgorithmSignal(
            algorithm="decision_orchestrator",
            symbol=intelligence.symbol,
            timeframe="multi_horizon",
            action=composite_action,
            score=50.0 + combined_score * 50.0,
            confidence=combined_confidence,
            expected_edge=None,
            reasoning=[
                "Composite signal from market intelligence and horizons."
            ],
        )

        decision = self.decision_core.decide([composite_signal], risk)
        position_decision = self.position_engine.decide(
            decision.action.value,
            position or PositionContext(),
        )

        reasoning = (
            f"intelligence={intelligence.direction} score={intelligence_score:.3f}",
            f"horizon={horizon.action.value} score={horizon_score:.3f}",
            f"combined_score={combined_score:.3f}",
            f"combined_confidence={combined_confidence:.3f}",
            f"decision={decision.action.value}: {decision.reason}",
            f"position={position_decision.action.value}: {position_decision.reason}",
        )

        return OrchestrationResult(
            symbol=intelligence.symbol,
            decision=decision,
            position=position_decision,
            combined_score=combined_score,
            combined_confidence=combined_confidence,
            reasoning=reasoning,
        )

    @staticmethod
    def _horizon_score(result: MultiHorizonResult) -> float:
        score = (result.score - 50.0) / 50.0
        if result.action is Action.BUY:
            return abs(score)
        if result.action is Action.SELL:
            return -abs(score)
        return 0.0

    @staticmethod
    def _action_from_score(score: float) -> Action:
        if score >= 0.55:
            return Action.BUY
        if score <= -0.55:
            return Action.SELL
        return Action.HOLD

    @staticmethod
    def _normalise_horizon_confidence(value: float) -> float:
        return max(0.0, min(1.0, value / 100.0))

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    @staticmethod
    def _clamp_signed(value: float) -> float:
        return max(-1.0, min(1.0, value))
