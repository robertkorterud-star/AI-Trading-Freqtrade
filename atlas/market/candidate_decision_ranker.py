from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult
from atlas.market.candidate_ranking_evidence import (
    CandidateRankingEvidence,
)
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
    def build_evidence(
        cls,
        decision: DecisionResult,
        regime_decision=None,
    ) -> CandidateRankingEvidence:
        'Build an explainable representation of the ranking.'

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

        final_score = (
            base_score * 0.80
            + regime_fit * 0.20
        )

        final_score = round(
            max(
                0.0,
                min(
                    100.0,
                    final_score,
                ),
            ),
            4,
        )

        return CandidateRankingEvidence(
            symbol=decision.symbol,
            base_score=round(base_score, 4),
            regime_fit=regime_fit,
            final_score=final_score,
            regime=getattr(
                regime_decision,
                "regime",
                None,
            ),
            strategy=getattr(
                regime_decision,
                "strategy",
                None,
            ),
            regime_confidence=float(
                getattr(
                    regime_decision,
                    "confidence",
                    0.0,
                )
            ),
            independent_run_count=int(
                getattr(
                    regime_decision,
                    "independent_run_count",
                    0,
                )
            ),
            robust_winner=bool(
                getattr(
                    regime_decision,
                    "robust_winner",
                    False,
                )
            ),
        )

    @classmethod
    def score(
        cls,
        decision: DecisionResult,
        regime_decision=None,
    ) -> float:
        'Calculate a comparable decision-quality score.'

        return cls.build_evidence(
            decision,
            regime_decision,
        ).final_score

    @classmethod
    def _sort_key(
        cls,
        decision: DecisionResult,
        regime_decision=None,
    ):
        return (
            cls.ACTION_PRIORITY.get(
                decision.action,
                0,
            ),
            cls.score(
                decision,
                regime_decision,
            ),
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
            key=lambda decision: self._sort_key(
                decision,
                regime_decisions.get(
                    decision.symbol
                ),
            ),
            reverse=True,
        )

        return valid

    def rank_with_evidence(
        self,
        decisions: list[DecisionResult],
        investable_only: bool = False,
        regime_decisions=None,
    ) -> list[CandidateRankingEvidence]:
        'Return ranking evidence in the same order as ranked decisions.'

        regime_decisions = regime_decisions or {}

        ranked = self.rank(
            decisions,
            investable_only=investable_only,
            regime_decisions=regime_decisions,
        )

        return [
            self.build_evidence(
                decision,
                regime_decisions.get(
                    decision.symbol
                ),
            )
            for decision in ranked
        ]
