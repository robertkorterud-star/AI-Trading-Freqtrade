"""
Base class for all ATLAS agents.
"""

from abc import ABC, abstractmethod
from atlas.shared.types import AgentResult


class BaseAgent(ABC):
    """
    Abstract base class for all ATLAS agents.

    Every agent must implement the analyze() method
    and return an AgentResult.
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def analyze(self, data) -> AgentResult:
        """
        Analyze market data and return a standardized result.
        """
        pass