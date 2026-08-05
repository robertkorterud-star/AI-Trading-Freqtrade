"""
Analysis Service

Runs all registered analysts.
"""

from atlas.core.registry import AgentRegistry
from atlas.models.analysis_result import AnalysisResult


class AnalysisService:
    """Runs all registered analysts."""

    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    def analyze(self, symbol: str) -> list[AnalysisResult]:
        return self.registry.analyze_all(symbol)