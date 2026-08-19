"""
ATLAS Intelligence Summary

Summarizes agreement and conflict between analysts.
"""

from dataclasses import dataclass, field

from atlas.models.action import Action


@dataclass(slots=True)
class IntelligenceSummary:
    """Combined intelligence from ATLAS analysts."""

    symbol: str

    action: Action

    evidence: float

    confidence: float

    buy_count: int

    hold_count: int

    sell_count: int

    agreement: float

    conflict: bool

    analysts: list[str] = field(default_factory=list)

    reasoning: list[str] = field(default_factory=list)
