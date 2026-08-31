"""
ATLAS Decision Core

Converts multi-horizon and fused algorithm signals into an actionable
BUY / HOLD / SELL decision while applying confidence and risk gates.

This layer is intentionally horizon-agnostic. ATLAS can use it for
intraday, swing, or longer-term decisions.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping

from atlas.algorithms.base import Action


class DecisionAction(str, Enum):
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"


@dataclass(frozen=True)
class RiskContext:
    """Current risk state supplied to the decision core."""

    risk_score: float = 0.0
    volatility_score: float = 0.0
    drawdown_score: float = 0.0
    position_score: float = 0.0


@dataclass(frozen=True)
class DecisionResult:
    """Final ATLAS trading decision."""

    action: DecisionAction
    confidence: float
    risk_score: float
    score: float
    reason: str


class DecisionCore:
    """
    Final decision gate for ATLAS.

    The core deliberately separates signal strength from risk. A strong
    signal can still become HOLD when the risk environment is unsafe.
    """

    def __init__(
        self,
        buy_threshold: float = 0.55,
        sell_threshold: float = -0.55,
        minimum_confidence: float = 0.55,
        maximum_risk: float = 0.70,
        fusion_weight: float = 1.50,
        horizon_weight: float = 1.25,
        agent_weight: float = 0.75,
        signal_weights: Mapping[str, float] | None = None,
    ):
        if not 0.0 <= buy_threshold <= 1.0:
            raise ValueError("buy_threshold must be between 0 and 1")

        if not -1.0 <= sell_threshold <= 0.0:
            raise ValueError("sell_threshold must be between -1 and 0")

        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be between 0 and 1")

        if not 0.0 <= maximum_risk <= 1.0:
            raise ValueError("maximum_risk must be between 0 and 1")

        if fusion_weight <= 0.0:
            raise ValueError("fusion_weight must be greater than 0")

        if horizon_weight <= 0.0:
            raise ValueError("horizon_weight must be greater than 0")

        if agent_weight <= 0.0:
            raise ValueError("agent_weight must be greater than 0")

        configured_weights = dict(signal_weights or {})
        for source, weight in configured_weights.items():
            if weight <= 0.0:
                raise ValueError(
                    f"signal weight for {source!r} must be greater than 0"
                )

        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.minimum_confidence = minimum_confidence
        self.maximum_risk = maximum_risk
        self.fusion_weight = fusion_weight
        self.horizon_weight = horizon_weight
        self.agent_weight = agent_weight
        self.signal_weights = configured_weights

    def decide(
        self,
        signals: Iterable,
        risk: RiskContext | None = None,
    ) -> DecisionResult:
        """
        Produce a final decision from algorithm signals.

        Signals are expected to expose:
        - action
        - confidence

        BUY contributes positively, SELL negatively and HOLD neutrally.
        Confidence weights the contribution of each directional signal.
        Signal source weights can further tune the influence of fusion,
        multi-horizon and agent signals.
        """

        signal_list = list(signals)

        if not signal_list:
            return DecisionResult(
                action=DecisionAction.HOLD,
                confidence=0.0,
                risk_score=0.0,
                score=0.0,
                reason="no signals",
            )

        weighted_scores = []
        weighted_confidences = []
        total_weight = 0.0

        for signal in signal_list:
            confidence = self._clamp(
                float(getattr(signal, "confidence", 0.0))
            )
            action = getattr(signal, "action", Action.HOLD)

            action_value = getattr(action, "value", action)

            if action is Action.BUY:
                direction = 1.0
            elif action is Action.SELL:
                direction = -1.0
            elif str(action_value).strip().lower() == "buy":
                direction = 1.0
            elif str(action_value).strip().lower() == "sell":
                direction = -1.0
            else:
                direction = 0.0

            if hasattr(signal, "score"):
                signal_score = self._clamp(
                    abs(float(getattr(signal, "score")))
                )
                weighted_score = direction * signal_score * confidence
            else:
                weighted_score = direction * confidence

            weight = self._signal_weight(signal)
            weighted_scores.append(weighted_score * weight)
            weighted_confidences.append(confidence * weight)
            total_weight += weight

        score = sum(weighted_scores) / total_weight
        confidence = sum(weighted_confidences) / total_weight

        risk_score = self._calculate_risk(risk)

        if risk_score > self.maximum_risk:
            return DecisionResult(
                action=DecisionAction.HOLD,
                confidence=confidence,
                risk_score=risk_score,
                score=score,
                reason="risk gate blocked decision",
            )

        if confidence < self.minimum_confidence:
            return DecisionResult(
                action=DecisionAction.HOLD,
                confidence=confidence,
                risk_score=risk_score,
                score=score,
                reason="confidence below minimum",
            )

        if score >= self.buy_threshold:
            return DecisionResult(
                action=DecisionAction.BUY,
                confidence=confidence,
                risk_score=risk_score,
                score=score,
                reason="buy consensus passed risk gate",
            )

        if score <= self.sell_threshold:
            return DecisionResult(
                action=DecisionAction.SELL,
                confidence=confidence,
                risk_score=risk_score,
                score=score,
                reason="sell consensus passed risk gate",
            )

        return DecisionResult(
            action=DecisionAction.HOLD,
            confidence=confidence,
            risk_score=risk_score,
            score=score,
            reason="no directional consensus",
        )

    def _signal_weight(self, signal) -> float:
        """Return the configured influence weight for a signal source."""

        algorithm = str(getattr(signal, "algorithm", "")).strip().lower()
        configured_weight = self.signal_weights.get(algorithm)

        if configured_weight is not None:
            return configured_weight

        if algorithm == "signal_fusion":
            return self.fusion_weight

        if algorithm == "multi_horizon":
            return self.horizon_weight

        if algorithm.startswith("agent:"):
            return self.agent_weight

        return 1.0

    @staticmethod
    def _calculate_risk(risk: RiskContext | None) -> float:
        if risk is None:
            return 0.0

        values = (
            DecisionCore._clamp(risk.risk_score),
            DecisionCore._clamp(risk.volatility_score),
            DecisionCore._clamp(risk.drawdown_score),
            DecisionCore._clamp(risk.position_score),
        )

        return sum(values) / len(values)

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))
