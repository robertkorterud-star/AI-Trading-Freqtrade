"""
ATLAS Candidate Regime Fit Scorer.

Calculates how strongly an existing decision is supported by
strategy-memory context for the current market regime.

Research-only.
This component does not create BUY/SELL signals.
"""

from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult
from atlas.trading.strategy_memory_regime_decision_adapter import (
    StrategyMemoryRegimeDecision,
)


class CandidateRegimeFitScorer:
    """
    Score the compatibility between a decision and regime memory.

    The scorer is deliberately conservative:

    - No regime decision -> neutral score.
    - No strategy recommendation -> neutral score.
    - Non-robust recommendation -> neutral score.
    - HOLD remains neutral and cannot become a BUY/SELL signal.
    - A concrete strategy recommendation contributes only as
      contextual evidence for later ranking.
    """

    NEUTRAL_SCORE = 50.0
    SUPPORTED_SCORE = 100.0
    UNSUPPORTED_SCORE = 0.0

    @classmethod
    def score(
        cls,
        decision: DecisionResult,
        regime_decision: StrategyMemoryRegimeDecision | None,
    ) -> float:
        """
        Return a 0-100 regime-fit score.

        Strategy-memory does not define trade direction here.
        It only indicates whether the existing decision is compatible
        with a robust regime-memory recommendation.
        """

        if regime_decision is None:
            return cls.NEUTRAL_SCORE

        if decision.symbol != regime_decision.symbol:
            raise ValueError(
                "Decision and regime decision symbols must match."
            )

        if (
            not regime_decision.strategy
            or not regime_decision.robust_winner
        ):
            return cls.NEUTRAL_SCORE

        if decision.action == Action.HOLD:
            return cls.NEUTRAL_SCORE

        # At this stage strategy-memory identifies contextual support,
        # but does not map individual strategy names to trade actions.
        #
        # Therefore a concrete BUY/SELL decision receives the
        # recommendation confidence as its regime-fit evidence.
        return round(
            max(
                0.0,
                min(
                    100.0,
                    float(regime_decision.confidence),
                ),
            ),
            4,
        )
