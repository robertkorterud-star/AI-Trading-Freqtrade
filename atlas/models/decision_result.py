"""
Decision Result

Final decision returned by the Decision Engine.
"""

from dataclasses import dataclass, field

from atlas.models.action import Action


@dataclass(slots=True)
class DecisionResult:
    """
    Final decision made by ATLAS.
    """

    symbol: str

    action: Action

    confidence: float

    evidence: float

    analysts: list[str] = field(default_factory=list)

    agent_weights: dict[str, float] = field(
        default_factory=dict
    )

    dominant_action: Action | None = None

    dominant_weight: float = 0.0

    action_support_analyst: str | None = None

    action_support_action: Action | None = None

    action_support_weight: float = 0.0

    opposing_analysts: list[str] = field(
        default_factory=list
    )

    adaptive_override: bool = False

    decision_margin: float = 0.0

    robustness: float = 0.0

    robustness_level: str = "WEAK"

    reasoning: list[str] = field(default_factory=list)