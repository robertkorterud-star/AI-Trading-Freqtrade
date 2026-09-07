"""
ATLAS Strategy Memory Regime Decision Integration.

Combines an existing decision with regime strategy-memory context.

Research-only.
This module does not execute trades and does not create BUY/SELL
signals from strategy memory alone.
"""

from atlas.models.decision_result import DecisionResult
from atlas.trading.strategy_memory_regime_decision_adapter import (
    StrategyMemoryRegimeDecision,
)


class StrategyMemoryRegimeDecisionIntegration:
    """
    Add regime strategy-memory context to an existing decision.

    The existing DecisionResult remains authoritative for the action.
    Strategy memory can explain and contextualize the decision, but
    cannot independently create a trade action.
    """

    def integrate(
        self,
        decision: DecisionResult,
        regime_decision: StrategyMemoryRegimeDecision,
    ) -> DecisionResult:
        if decision.symbol != regime_decision.symbol:
            raise ValueError(
                "Decision and regime decision symbols must match."
            )

        reasoning = list(decision.reasoning)

        reasoning.append(
            f"Strategy-memory regime: "
            f"{regime_decision.regime}."
        )

        if regime_decision.strategy:
            reasoning.append(
                f"Strategy-memory recommendation: "
                f"{regime_decision.strategy} "
                f"(confidence "
                f"{regime_decision.confidence:.1f}/100, "
                f"{regime_decision.independent_run_count} "
                f"independent runs)."
            )

            if regime_decision.robust_winner:
                reasoning.append(
                    "Strategy-memory recommendation is supported "
                    "by a robust historical regime winner."
                )
        else:
            reasoning.append(
                "No robust strategy-memory recommendation "
                "is available for this regime."
            )

        return DecisionResult(
            symbol=decision.symbol,
            action=decision.action,
            confidence=decision.confidence,
            evidence=decision.evidence,
            analysts=list(decision.analysts),
            agent_weights=dict(decision.agent_weights),
            dominant_action=decision.dominant_action,
            dominant_weight=decision.dominant_weight,
            action_support_analyst=decision.action_support_analyst,
            action_support_action=decision.action_support_action,
            action_support_weight=decision.action_support_weight,
            opposing_analysts=list(decision.opposing_analysts),
            adaptive_override=decision.adaptive_override,
            decision_margin=decision.decision_margin,
            robustness=decision.robustness,
            robustness_level=decision.robustness_level,
            reasoning=reasoning,
            expected_return=decision.expected_return,
            ensemble_action=decision.ensemble_action,
            ensemble_confidence=decision.ensemble_confidence,
            risk_assessment=decision.risk_assessment,
            portfolio_assessment=decision.portfolio_assessment,
        )
