from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult
from atlas.market.candidate_regime_fit_scorer import (
    CandidateRegimeFitScorer,
)


class CandidateDecisionRanker:
    'Rank candidate decisions by decision quality.'

    CONFIDENCE_WEIGHT = 0.25
    EVIDENCE_WEIGHT = 0.25
    ROBUSTNESS_WEIGHT = 0.30
    MARGIN_WEIGHT = 0.20

    ACTION_PRIORITY = {
        Action.BUY: 2,
        Action.SELL: 1,
        Action.HOLD: 0,
    }

    @classmethod
    def score(
        cls,
        decision: DecisionResult,
        regime_decision=None,
    ) -> float:
        'Calculate a comparable decision-quality score.'

        base_score = (
            float(decision.confidence)
            * cls.CONFIDENCE_WEIGHT
            + float(decision.evidence)
            * cls.EVIDENCE_WEIGHT
            + float(decision.robustness)
            * cls.ROBUSTNESS_WEIGHT
            + float(decision.decision_margin)
            * cls.MARGIN_WEIGHT
        )

        regime_fit = CandidateRegimeFitScorer.score(
            decision,
            regime_decision,
        )

        score = (
            base_score * 0.80
            + regime_fit * 0.20
        )

        return round(
            max(
                0.0,
                min(
                    100.0,
                    score,
                ),
            ),
            4,
        )

    @classmethod
    def _sort_key(
        cls,
        decision: DecisionResult,
    ):
        return (
            cls.ACTION_PRIORITY.get(
                decision.action,
                0,
            ),
            cls.score(decision),
        )

    def rank(
        self,
        decisions: list[DecisionResult],
        investable_only: bool = False,
        regime_decisions=None,
    ) -> list[DecisionResult]:
        'Return decisions ranked strongest first.'

        valid = list(decisions)

        if investable_only:
            valid = [
                decision
                for decision in valid
                if decision.action in {
                    Action.BUY,
                    Action.SELL,
                }
            ]

        regime_decisions = regime_decisions or {}

        valid.sort(
            key=lambda decision: (
                self.ACTION_PRIORITY.get(
                    decision.action,
                    0,
                ),
                self.score(
                    decision,
                    regime_decisions.get(
                        decision.symbol
                    ),
                ),
            ),
            reverse=True,
        )

        return valid
