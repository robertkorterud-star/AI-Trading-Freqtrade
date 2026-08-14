"""
Intelligence Analyst

Combines external research sources into a standardized
ATLAS analysis result.
"""

from atlas.agents.base_agent import BaseAgent
from atlas.adapters.intelligence_sources import (
    IntelligenceSourceAdapter,
)
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult


class IntelligenceAnalyst(BaseAgent):
    """Analyzes external intelligence sources."""

    def __init__(self) -> None:
        super().__init__("Intelligence Analyst")
        self.sources = IntelligenceSourceAdapter()

    def analyze(self, symbol: str) -> AnalysisResult:
        """Analyze available external research."""

        sources = self.sources.get(symbol)

        if not sources:
            return AnalysisResult(
                analyst=self.name,
                symbol=symbol,
                action=Action.HOLD,
                confidence=50.0,
                evidence=50.0,
                reasoning=[
                    "No external intelligence sources available."
                ],
            )

        positive = sum(
            1
            for item in sources
            if item.get("sentiment") == "positive"
        )

        negative = sum(
            1
            for item in sources
            if item.get("sentiment") == "negative"
        )

        neutral = sum(
            1
            for item in sources
            if item.get("sentiment") == "neutral"
        )

        total = len(sources)

        reasoning = [
            f"{total} intelligence sources analyzed."
        ]

        reasoning.append(
            f"{positive} positive, "
            f"{negative} negative, "
            f"{neutral} neutral."
        )

        if positive > negative:
            action = Action.BUY
            confidence = 85.0
            evidence = 95.0

            reasoning.append(
                "External intelligence is predominantly positive."
            )

        elif negative > positive:
            action = Action.SELL
            confidence = 60.0
            evidence = 45.0

            reasoning.append(
                "External intelligence is predominantly negative."
            )

        else:
            action = Action.HOLD
            confidence = 50.0
            evidence = 50.0

            reasoning.append(
                "External intelligence is mixed or neutral."
            )

        return AnalysisResult(
            analyst=self.name,
            symbol=symbol,
            action=action,
            confidence=confidence,
            evidence=evidence,
            reasoning=reasoning,
        )
