"""
ATLAS Decision Orchestrator.

Combines algorithm signals, multi-horizon intelligence and agent
observations into one auditable, risk-gated trading decision.

This layer decides.
It does not execute orders.
"""

from dataclasses import dataclass

from atlas.algorithms.base import AlgorithmSignal
from atlas.algorithms.pipeline import AlgorithmPipeline
from atlas.algorithms.decision_core import (
    DecisionCore,
    DecisionResult,
    RiskContext,
)
from atlas.algorithms.multi_horizon import (
    HorizonSignal,
    MultiHorizonDecisionEngine,
)


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
    """Coordinate intelligence, horizons and the final risk gate."""

    def __init__(
        self,
        decision_core: DecisionCore | None = None,
        horizon_engine: MultiHorizonDecisionEngine | None = None,
        algorithm_pipeline: AlgorithmPipeline | None = None,
    ):
        self.decision_core = decision_core or DecisionCore()
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
    ) -> OrchestrationResult:
        """Run the complete decision chain without executing a trade."""

        self._validate_symbols(symbol, signals)

        horizon_result = None
        fusion_result = None
        decision_inputs = list(signals)

        if self.algorithm_pipeline is not None and market_data is not None:
            fusion_result, pipeline_signals = (
                self.algorithm_pipeline.analyze(
                    symbol,
                    market_data,
                )
            )

            if pipeline_signals:
                self._validate_symbols(
                    symbol,
                    pipeline_signals,
                )

            if fusion_result is not None:
                decision_inputs.append(
                    AlgorithmSignal(
                        algorithm="signal_fusion",
                        symbol=symbol,
                        timeframe=fusion_result.timeframe,
                        action=fusion_result.action,
                        score=fusion_result.score,
                        confidence=(
                            fusion_result.confidence / 100.0
                        ),
                        reasoning=list(
                            fusion_result.reasoning
                        ),
                    )
                )

        if horizons:
            horizon_result = self.horizon_engine.decide(
                symbol,
                horizons,
            )

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

        decision = self.decision_core.decide(
            decision_inputs,
            risk,
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

    @staticmethod
    def _validate_symbols(
        symbol: str,
        signals: list[AlgorithmSignal],
    ) -> None:
        for signal in signals:
            if signal.symbol != symbol:
                raise ValueError(
                    "all algorithm signals must match symbol"
                )
