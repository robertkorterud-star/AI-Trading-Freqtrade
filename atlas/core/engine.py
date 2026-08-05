"""
ATLAS Engine
"""

from atlas.core.config import AtlasConfig
from atlas.core.logger import get_logger
from atlas.core.registry import AgentRegistry
from atlas.core.analysis_service import AnalysisService

from atlas.agents.news_analyst import NewsAnalyst
from atlas.decision.engine import DecisionEngine


class AtlasEngine:
    """Main entry point for ATLAS."""

    def __init__(self):

        self.config = AtlasConfig()

        self.logger = get_logger("ATLAS")

        self.registry = AgentRegistry()

        self.registry.register(NewsAnalyst())

        self.analysis_service = AnalysisService(self.registry)

        self.decision_engine = DecisionEngine()

    def start(self):

        self.logger.info("Starting ATLAS")

        self.logger.info(f"Version: {self.config.version}")

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

        decision = self.decision_engine.evaluate(results)

        self.logger.info("")
        self.logger.info("=" * 40)
        self.logger.info("FINAL DECISION")
        self.logger.info("=" * 40)

        self.logger.info(f"Symbol      : {decision.symbol}")
        self.logger.info(f"Decision    : {decision.action.value}")
        self.logger.info(f"Evidence    : {decision.evidence:.1f}")
        self.logger.info(f"Confidence  : {decision.confidence:.1f}")

        self.logger.info("")
        self.logger.info("ATLAS is ready.")


if __name__ == "__main__":
    AtlasEngine().start()