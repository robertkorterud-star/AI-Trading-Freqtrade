"""ATLAS Candidate Intelligence v1.

Turns scanner evidence into a transparent research score.  This layer is
read-only: it does not produce BUY/SELL actions and never places orders.
"""

from dataclasses import dataclass

from atlas.market.market_scout import ScoutEvidence


@dataclass(frozen=True, slots=True)
class CandidateIntelligenceInput:
    """Optional deeper evidence that can be added after scanning."""

    prediction_accuracy: float = 0.0
    strategy_evidence: float = 0.0
    robustness: float = 0.0
    downside_risk: float = 0.0
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class CandidateIntelligence:
    """Explainable research assessment for one candidate."""

    symbol: str
    asset_type: str
    overall_score: float
    scanner_score: float
    technical_score: float
    catalyst_score: float
    liquidity_score: float
    prediction_accuracy: float
    strategy_evidence: float
    robustness: float
    downside_risk: float
    confidence: float
    reasons: tuple[str, ...]
    explanation: str


class CandidateIntelligenceService:
    """Build deterministic, explainable intelligence without trading."""

    SCANNER_WEIGHT = 0.40
    TECHNICAL_WEIGHT = 0.20
    CATALYST_WEIGHT = 0.10
    LIQUIDITY_WEIGHT = 0.10
    PREDICTION_WEIGHT = 0.05
    STRATEGY_WEIGHT = 0.05
    ROBUSTNESS_WEIGHT = 0.05
    DOWNSIDE_WEIGHT = 0.05

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(100.0, float(value)))

    def analyze(
        self,
        evidence: ScoutEvidence,
        deeper: CandidateIntelligenceInput | None = None,
    ) -> CandidateIntelligence:
        """Create research intelligence from scanner and optional evidence."""
        deeper = deeper or CandidateIntelligenceInput()

        scanner = self._clamp(evidence.score)
        technical = self._clamp(
            evidence.momentum_score * 0.50
            + evidence.breakout_score * 0.30
            + evidence.volume_score * 0.20
        )
        catalyst = self._clamp(evidence.catalyst_score)
        liquidity = self._clamp(evidence.liquidity_score)
        prediction = self._clamp(deeper.prediction_accuracy)
        strategy = self._clamp(deeper.strategy_evidence)
        robustness = self._clamp(deeper.robustness)
        downside = self._clamp(deeper.downside_risk)

        overall = (
            scanner * self.SCANNER_WEIGHT
            + technical * self.TECHNICAL_WEIGHT
            + catalyst * self.CATALYST_WEIGHT
            + liquidity * self.LIQUIDITY_WEIGHT
            + prediction * self.PREDICTION_WEIGHT
            + strategy * self.STRATEGY_WEIGHT
            + robustness * self.ROBUSTNESS_WEIGHT
            + (100.0 - downside) * self.DOWNSIDE_WEIGHT
        )

        reasons = list(evidence.reasons)
        if prediction >= 70.0:
            reasons.append("strong historical prediction accuracy")
        if strategy >= 70.0:
            reasons.append("strong strategy evidence")
        if robustness >= 70.0:
            reasons.append("robust across independent evidence")
        if downside >= 60.0:
            reasons.append("elevated downside risk")

        confidence = self._clamp(
            deeper.confidence
            if deeper.confidence > 0.0
            else (
                scanner * 0.50
                + technical * 0.25
                + robustness * 0.25
            )
        )

        reason_text = ", ".join(reasons) if reasons else "no dominant catalyst"
        explanation = (
            f"{evidence.symbol}: intelligence score {overall:.1f}/100; "
            f"scanner {scanner:.1f}, technical {technical:.1f}, "
            f"catalyst {catalyst:.1f}, liquidity {liquidity:.1f}. "
            f"Why: {reason_text}."
        )

        return CandidateIntelligence(
            symbol=evidence.symbol,
            asset_type=evidence.asset_type.value,
            overall_score=round(overall, 4),
            scanner_score=round(scanner, 4),
            technical_score=round(technical, 4),
            catalyst_score=round(catalyst, 4),
            liquidity_score=round(liquidity, 4),
            prediction_accuracy=round(prediction, 4),
            strategy_evidence=round(strategy, 4),
            robustness=round(robustness, 4),
            downside_risk=round(downside, 4),
            confidence=round(confidence, 4),
            reasons=tuple(reasons),
            explanation=explanation,
        )

    def rank(
        self,
        candidates: list[ScoutEvidence],
    ) -> list[CandidateIntelligence]:
        """Rank scanner candidates by intelligence score."""
        results = [self.analyze(candidate) for candidate in candidates]
        results.sort(
            key=lambda item: (item.overall_score, item.symbol),
            reverse=True,
        )
        return results
