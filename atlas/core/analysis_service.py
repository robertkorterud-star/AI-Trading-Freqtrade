"""
Analysis Service

Runs all registered analysts.
"""

from atlas.core.registry import AgentRegistry
from atlas.models.analysis_result import AnalysisResult


class AnalysisService:
    """Runs all registered analysts."""

    def __init__(
        self,
        registry: AgentRegistry,
    ):
        self.registry = registry

    def analyze(
        self,
        symbol: str,
        exclude: set[str] | None = None,
    ) -> list[AnalysisResult]:
        return self.registry.analyze_all(
            symbol,
            exclude=exclude,
        )


    def analyze_with_news(
        self,
        symbol: str,
        news: list,
    ) -> list[AnalysisResult]:
        """Run all analysts, supplying news to News Analyst."""

        results = []

        for agent in self.registry.get_all():

            if agent.name == "News Analyst":
                results.append(
                    agent.analyze_news(
                        symbol,
                        news,
                    )
                )
            else:
                results.append(
                    agent.analyze(symbol)
                )

        return results
