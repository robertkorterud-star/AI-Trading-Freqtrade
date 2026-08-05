"""
ATLAS Engine
"""

from atlas.core.config import AtlasConfig
from atlas.core.logger import get_logger
from atlas.core.registry import AgentRegistry
from atlas.core.analysis_service import AnalysisService
from atlas.agents.news_analyst import NewsAnalyst


class AtlasEngine:
    """Main entry point for ATLAS."""

    def __init__(self):

        self.config = AtlasConfig()

        self.logger = get_logger("ATLAS")

        self.registry = AgentRegistry()

        # Register all analysts
        self.registry.register(NewsAnalyst())

        self.analysis_service = AnalysisService(self.registry)

    def start(self):

        self.logger.info("Starting ATLAS")

        self.logger.info(
            f"Version: {self.config.version}"
        )

        self.logger.info(
            f"Trading Mode: {self.config.trading_mode}"
        )

        self.logger.info(
            f"Capital Limit: {self.config.capital_limit}"
        )

        self.logger.info("")
        self.logger.info("Running market analysis...")

        results = self.analysis_service.analyze("BTC")

        for result in results:

            self.logger.info(
                f"{result.analyst}: "
                f"{result.action.value} | "
                f"Evidence={result.evidence} | "
                f"Confidence={result.confidence}"
            )

        self.logger.info("")
        self.logger.info("ATLAS is ready.")


if __name__ == "__main__":

    AtlasEngine().start()