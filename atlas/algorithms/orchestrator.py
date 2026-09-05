"""
ATLAS Decision Orchestrator.

Combines algorithm signals, multi-horizon intelligence and agent
observations into one auditable, risk-gated trading decision.

This layer assembles intelligence.
It does not execute orders or own the canonical final decision.
"""

from dataclasses import dataclass

from atlas.algorithms.base import AlgorithmSignal
from atlas.algorithms.pipeline import AlgorithmPipeline
from atlas.algorithms.decision_core import (
    DecisionAction,
    DecisionCore,
    DecisionResult,
    RiskContext,
)
from atlas.algorithms.multi_horizon import (
    HorizonSignal,
    MultiHorizonDecisionEngine,
)
from atlas.decision.engine import DecisionEngine
from atlas.models.action import Action
from atlas.portfolio.manager import PortfolioPosition
from atlas.risk.manager import RiskManager


@dataclass(frozen=True, slots=True)
class OrchestrationResult:
    """Auditable result of one complete ATLAS decision cycle."""

    symbol: str
    decision: DecisionResult
    horizon_result: object | None
    observations: tuple[object, ...]
    reasoning: tuple[str, ...]
    fusion_result: object | None = None


class DecisionOrchestrator:
    """Coordinate intelligence and delegate the final decision canonically."""

    def __init__(
        self,
        decision_core: DecisionCore | None = None,
        decision_engine: DecisionEngine | None = None,
        horizon_engine: MultiHorizonDecisionEngine | None = None,
        algorithm_pipeline: AlgorithmPipeline | None = None,
        risk_manager: RiskManager | None = None,
    ):
        # Explicit DecisionCore injection remains a compatibility seam for
        # legacy callers/tests. Normal ATLAS operation uses the canonical
        # DecisionEngine as the sole final-decision owner.
        self.decision_core = decision_core
        self.risk_manager = risk_manager
        self.decision_engine = decision_engine or DecisionEngine(
            risk_manager=risk_manager,
        )
        self.horizon_engine = (
            horizon_engine or MultiHorizonDecisionEngine()
        )
        self.algorithm_pipeline = algorithm_pipeline

    def decide(
        self,
        symbol: str,
        signals: list[AlgorithmSignal],
        horizons: list[HorizonSignal] | None = None,
        risk: RiskContext | None = None,
        observations: list[object] | None = None,
        market_data: dict | None = None,
        algorithm_signals: list[AlgorithmSignal] | None = None,
        fusion_result: object | None = None,
        price: float | None = None,
        equity: float | None = None,
        current_exposure_pct: float = 0.0,
        drawdown_pct: float = 0.0,
        portfolio_positions: list[PortfolioPosition] | tuple[PortfolioPosition, ...] = (),
    ) -> OrchestrationResult:
        """Run the complete decision chain without executing a trade.

        The orchestrator assembles raw algorithm, fusion, horizon and agent
        signals, then delegates the final directional decision to the
        canonical :class:`atlas.decision.engine.DecisionEngine`.

        When Signal Fusion is already available, its result is the canonical
        aggregate of the raw algorithm signals. Passing both the raw signals
        and the fusion result into the final decision would double-count the
        same algorithm evidence, so the raw signals are retained for audit
        and the fused result is used at the decision boundary.

        Explicit ``decision_core`` injection is retained only as a legacy
        compatibility seam while callers migrate to the canonical engine.
        """

        self._validate_symbols(symbol, signals)

        horizon_result = None
        decision_inputs = list(signals)

        if algorithm_signals is not None:
            self._validate_symbols(symbol, algorithm_signals)
            if fusion_result is None:
                decision_inputs.extend(algorithm_signals)
        elif self.algorithm_pipeline is not None and market_data is not None:
            fusion_result, pipeline_signals = (
                self.algorithm_pipeline.analyze(
                    symbol,
                    market_data,
                )
            )

            if pipeline_signals:
                self._validate_symbols(symbol, pipeline_signals)

            if fusion_result is None:
                decision_inputs.extend(pipeline_signals)

        if fusion_result is not None:
            self._validate_fusion_symbol(symbol, fusion_result)
            decision_inputs.append(
                AlgorithmSignal(
                    algorithm="signal_fusion",
                    symbol=symbol,
                    timeframe=fusion_result.timeframe,
                    action=fusion_result.action,
                    score=fusion_result.score,
                    confidence=fusion_result.confidence / 100.0,
                    reasoning=list(fusion_result.reasoning),
                )
            )

        if horizons:
            horizon_result = self.horizon_engine.decide(symbol, horizons)
            decision_inputs.append(
                AlgorithmSignal(
                    algorithm="multi_horizon",
                    symbol=symbol,
                    timeframe="multi",
                    action=horizon_result.action,
                    score=horizon_result.score,
                    confidence=horizon_result.confidence / 100.0,
                )
            )

        # Agent observations are converted into auditable signals so agent
        # intelligence reaches the canonical DecisionEngine.
        for observation in observations or []:
            observation_symbol = getattr(observation, "symbol", symbol)
            if observation_symbol != symbol:
                raise ValueError("all agent observations must match symbol")

            direction = str(getattr(observation, "direction", "neutral")).lower()
            if direction == "bullish":
                action = Action.BUY
            elif direction == "bearish":
                action = Action.SELL
            else:
                action = Action.HOLD

            decision_inputs.append(
                AlgorithmSignal(
                    algorithm=f"agent:{getattr(observation, 'agent', 'unknown')}",
                    symbol=symbol,
                    timeframe="agent",
                    action=action,
                    score=float(getattr(observation, "score", 0.0)),
                    confidence=float(getattr(observation, "confidence", 0.0)),
                    reasoning=[str(getattr(observation, "reason", ""))],
                )
            )

        decision = self._final_decision(
            decision_inputs,
            risk,
            price=price,
            equity=equity,
            current_exposure_pct=current_exposure_pct,
            drawdown_pct=drawdown_pct,
            portfolio_positions=portfolio_positions,
        )

        reasoning = (
            "ATLAS orchestration completed.",
            f"Algorithm signals: {len(decision_inputs)}.",
            f"Horizon signals: {len(horizons or [])}.",
            f"Agent observations: {len(observations or [])}.",
            f"Final action: {decision.action.value}.",
            f"Final score: {decision.score:.4f}.",
            f"Final confidence: {decision.confidence:.4f}.",
            f"Risk score: {decision.risk_score:.4f}.",
        )

        return OrchestrationResult(
            symbol=symbol,
            decision=decision,
            horizon_result=horizon_result,
            observations=tuple(observations or []),
            reasoning=reasoning,
            fusion_result=fusion_result,
        )

    def _final_decision(
        self,
        decision_inputs: list[AlgorithmSignal],
        risk: RiskContext | None,
        *,
        price: float | None = None,
        equity: float | None = None,
        current_exposure_pct: float = 0.0,
        drawdown_pct: float = 0.0,
        portfolio_positions: list[PortfolioPosition] | tuple[PortfolioPosition, ...] = (),
    ) -> DecisionResult:
        """Return the canonical decision, with a legacy compatibility seam."""
        if self.decision_core is not None:
            return self.decision_core.decide(decision_inputs, risk)

        if not decision_inputs:
            return DecisionResult(
                action=DecisionAction.HOLD,
                confidence=0.0,
                risk_score=0.0,
                score=0.0,
                reason="no signals",
            )

        canonical = self.decision_engine.evaluate_algorithm_signals(
            decision_inputs,
            price=price,
            equity=equity,
            current_exposure_pct=current_exposure_pct,
            drawdown_pct=drawdown_pct,
            portfolio_positions=portfolio_positions,
        )

        # Legacy RiskContext is retained only for callers that have not yet
        # migrated to the canonical RiskManager boundary. Once a RiskManager
        # is configured, all risk gating belongs to DecisionEngine.
        risk_score = self._risk_score(risk)
        if self.risk_manager is None and risk_score > 0.70 and canonical.action in {
            Action.BUY,
            Action.SELL,
        }:
            return DecisionResult(
                action=DecisionAction.HOLD,
                confidence=canonical.confidence / 100.0,
                risk_score=risk_score,
                score=self._compatibility_score(canonical),
                reason="risk gate blocked decision",
            )

        return DecisionResult(
            action=DecisionAction(canonical.action.value.lower()),
            confidence=canonical.confidence / 100.0,
            risk_score=(
                canonical.risk_assessment.risk_level == "BLOCKED"
                if canonical.risk_assessment is not None
                else risk_score
            ),
            score=self._compatibility_score(canonical),
            reason=self._reason_for_action(canonical.action),
        )

    @staticmethod
    def _compatibility_score(canonical) -> float:
        magnitude = max(0.0, min(1.0, canonical.evidence / 100.0))
        confidence = max(0.0, min(1.0, canonical.confidence / 100.0))
        score = magnitude * confidence
        if canonical.action is Action.SELL:
            return -score
        if canonical.action is Action.HOLD:
            return 0.0
        return score

    @staticmethod
    def _reason_for_action(action: Action) -> str:
        return {
            Action.BUY: "canonical decision: buy",
            Action.SELL: "canonical decision: sell",
            Action.HOLD: "canonical decision: hold",
            Action.WATCH: "canonical decision: watch",
        }[action]

    @staticmethod
    def _risk_score(risk: RiskContext | None) -> float:
        if risk is None:
            return 0.0
        values = (
            risk.risk_score,
            risk.volatility_score,
            risk.drawdown_score,
            risk.position_score,
        )
        return sum(values) / len(values)

    @staticmethod
    def _validate_symbols(symbol: str, signals: list[AlgorithmSignal]) -> None:
        if any(signal.symbol != symbol for signal in signals):
            raise ValueError("all signals must match symbol")

    @staticmethod
    def _validate_fusion_symbol(symbol: str, fusion_result) -> None:
        if fusion_result.symbol != symbol:
            raise ValueError("fusion result must match symbol")
