"""
Structured News Explanation

Human-readable explanation of AI news analysis.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class NewsExplanation:
    """
    Structured explanation of news analysis.
    """

    symbol: str

    sentiment: str

    relevance: float

    impact: str

    time_horizon: str

    action: str

    confidence: float

    reason: str
