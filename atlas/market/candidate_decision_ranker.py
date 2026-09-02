from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult
from atlas.market.candidate_ranking_evidence import (
    CandidateRankingEvidence,
)
from atlas.market.candidate_regime_fit_scorer import (
    CandidateRegimeFitScorer,
)
from atlas.trading.trading_cost_model import TradingCostModel


class CandidateDecisionRanker:
    'Rank candidate decisions by decision quality.'

    CONFIDENCE_WEIGHT = 0.20
    EVIDENCE_WEIGHT = 0.20
    ROBUSTNESS_WEIGHT = 0.15
    MARGIN_WEIGHT = 0.10
    NET_RETURN_WEIGHT = 0.35

    ACTION_PRIORITY = {
        Action.BUY: 2,
        Action.SELL: 1,
        Action.HOLD: 0,
    }

    def __init__(self, cost_model=None):
        self.cost_model = cost_model or TradingCostModel()

    def _net_return_details(self, decision: DecisionResult):
        """Return gross, net and risk-adjusted expected return."""
        gross_return = float(getattr(decision, "expected_return", 0.0))
        net_return = self.cost_model.net_return(gross_return)
        risk_adjusted = net_return * (
            max(0.0, min(100.0, float(decision.robustness))) / 100.0
        )
        return gross_return, net_return, risk_adjusted

    @staticmethod
    def _net_return_score(risk_adjusted_net_return: float) -> float:
        """Map risk-adjusted net return to a stable 0-100 ranking score."""
        score = 50.0 + risk_adjusted_net_return * 1000.0
        return max(0.0, min(100.0, score))

    @classmethod
    def build_evidence(
        cls,
        decision: DecisionResult,
        regime_decision=None,
    ) -> CandidateRankingEvidence:
        'Build an explainable representation of the ranking.'

        # Keep the cost model deterministic and configurable at instance level.
        # This classmethod remains for backwards compatibility and uses defaults.
        cost_model = TradingCostModel()
        gross_return = float(getattr(decision, "expected_return", 0.0))
        net_return = cost_model.net_return(gross_return)
        risk_adjusted_net_return = net_return * (
            max(0.0, min(100.0, float(decision.robustness))) / 100.0
        )
        net_return_score = CandidateDecisionRanker._net_return_score(
            risk_adjusted_net_return
        )

        base_score = (
            float(decision.confidence)
            * CandidateDecisionRanker.CONFIDENCE_WEIGHT
            + float(decision.evidence)
            * CandidateDecisionRanker.EVIDENCE_WEIGHT
            + float(decision.robustness)
            * CandidateDecisionRanker.ROBUSTNESS_WEIGHT
            + float(decision.decision_margin)
            * CandidateDecisionRanker.MARGIN_WEIGHT
            + net_return_score
            * CandidateDecisionRanker.NET_RETURN_WEIGHT
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
            expected_return=gross_return,
            net_expected_return=net_return,
            risk_adjusted_net_return=risk_adjusted_net_return,
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

    def build_evidence_with_cost_model(
        self,
        decision: DecisionResult,
        regime_decision=None,
    ) -> CandidateRankingEvidence:
        """Build evidence using this ranker's configured cost model."""
        gross_return, net_return, risk_adjusted_net_return = (
            self._net_return_details(decision)
        )
        net_return_score = self._net_return_score(
            risk_adjusted_net_return
        )

        base_score = (
            float(decision.confidence) * self.CONFIDENCE_WEIGHT
            + float(decision.evidence) * self.EVIDENCE_WEIGHT
            + float(decision.robustness) * self.ROBUSTNESS_WEIGHT
            + float(decision.decision_margin) * self.MARGIN_WEIGHT
            + net_return_score * self.NET_RETURN_WEIGHT
        )

        regime_fit = CandidateRegimeFitScorer.score(
            decision,
            regime_decision,
        )
        final_score = round(
            max(0.0, min(100.0, base_score * 0.80 + regime_fit * 0.20)),
            4,
        )

        return CandidateRankingEvidence(
            symbol=decision.symbol,
            base_score=round(base_score, 4),
            regime_fit=regime_fit,
            final_score=final_score,
            expected_return=gross_return,
            net_expected_return=net_return,
            risk_adjusted_net_return=risk_adjusted_net_return,
            regime=getattr(regime_decision, "regime", None),
            strategy=getattr(regime_decision, "strategy", None),
            regime_confidence=float(getattr(regime_decision, "confidence", 0.0)),
            independent_run_count=int(
                getattr(regime_decision, "independent_run_count", 0)
            ),
            robust_winner=bool(getattr(regime_decision, "robust_winner", False)),
        )

    def score(
        self,
        decision: DecisionResult,
        regime_decision=None,
    ) -> float:
        'Calculate a comparable decision-quality score.'

        return self.build_evidence_with_cost_model(
            decision,
            regime_decision,
        ).final_score

    def _sort_key(
        self,
        decision: DecisionResult,
        regime_decision=None,
    ):
        return (
            self.ACTION_PRIORITY.get(
                decision.action,
                0,
            ),
            self.score(
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
            self.build_evidence_with_cost_model(
                decision,
                regime_decisions.get(
                    decision.symbol
                ),
            )
            for decision in ranked
        ]
