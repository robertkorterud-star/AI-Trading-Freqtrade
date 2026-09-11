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

    # Optional confidence emitted by the underlying signal engine.
    # This preserves the existing analyst confidence contract.
    signal_confidence: float | None = None

    # Optional structured analyst metadata persisted in canonical snapshots.
    # Analysts may use this for source/context data that materially informed
    # their result without changing the common reasoning contract.
    metadata: dict = field(default_factory=dict)
