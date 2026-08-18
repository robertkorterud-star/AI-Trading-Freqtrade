"""
Base class for all ATLAS analysts.
"""

from abc import ABC, abstractmethod

from atlas.core.config import AtlasConfig
from atlas.i18n.translations import translate
from atlas.models.analysis_result import AnalysisResult


class BaseAgent(ABC):
    """Base class for every analyst."""

    def __init__(
        self,
        name: str,
        config: AtlasConfig | None = None,
    ):
        self.name = name
        self.config = config or AtlasConfig()

    def t(self, key: str) -> str:
        """Return translated text using the active ATLAS language."""
        return translate(self.config.language, key)

    @abstractmethod
    def analyze(self, symbol: str) -> AnalysisResult:
        """
        Analyze one symbol and return a standardized result.
        """
        raise NotImplementedError
