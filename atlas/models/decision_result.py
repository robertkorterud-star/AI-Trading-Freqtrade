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

    reasoning: list[str] = field(default_factory=list)