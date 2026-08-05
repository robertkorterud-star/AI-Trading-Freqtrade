"""
Base class for all ATLAS analysts.
"""

from abc import ABC, abstractmethod

from atlas.models.analysis_result import AnalysisResult


class BaseAgent(ABC):
    """Base class for every analyst."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def analyze(self, symbol: str) -> AnalysisResult:
        """
        Analyze one symbol and return a standardized result.
        """
        raise NotImplementedError