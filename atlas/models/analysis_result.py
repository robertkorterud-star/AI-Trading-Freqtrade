"""
Analysis Result

Every analyst in ATLAS returns this object.
"""

from dataclasses import dataclass, field

from atlas.models.action import Action


@dataclass(slots=True)
class AnalysisResult:
    """
    Standard result returned by every analyst.
    """

    analyst: str

    symbol: str

    action: Action

    confidence: float

    evidence: float

    reasoning: list[str] = field(default_factory=list)