"""
Structured Decision Explanation

Human-readable explanation of an ATLAS decision.
"""

from dataclasses import dataclass, field

from atlas.models.action import Action


@dataclass(slots=True)
class DecisionExplanation:
    """
    Structured explanation derived from a DecisionResult.
    """

    action: Action

    headline: str

    summary: str

    evidence: float

    confidence: float

    agreement: float

    dominant_action: Action | None = None

    dominant_weight: float = 0.0

    decision_margin: float = 0.0

    robustness: float = 0.0

    robustness_level: str = "WEAK"

    opposing_analysts: list[str] = field(
        default_factory=list
    )

    adaptive_override: bool = False

    key_reasons: list[str] = field(
        default_factory=list
    )
