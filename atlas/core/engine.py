"""
ATLAS Engine
"""

from atlas.agents.technical_analyst import TechnicalAnalyst
from atlas.core.config import AtlasConfig
from atlas.core.logger import get_logger
from atlas.core.registry import AgentRegistry
from atlas.core.analysis_service import AnalysisService

from atlas.agents.news_analyst import NewsAnalyst

from atlas.decision.engine import DecisionEngine

from atlas.report.report_builder import ReportBuilder

from atlas.risk.risk_engine import RiskEngine
from atlas.services.portfolio_service import PortfolioService
from atlas.trading.paper_trading_engine import PaperTradingEngine
from atlas.trading.trading_controller import TradingController
from atlas.trading.trading_runtime import TradingRuntime
from atlas.trading.trading_service import TradingService


class AtlasEngine:
    """Main entry point for ATLAS."""

    def __init__(self):

        self.config = AtlasConfig()

        self.logger = get_logger("ATLAS")

        self.registry = AgentRegistry()

        self.registry.register(NewsAnalyst())
        self.registry.register(TechnicalAnalyst())

        self.analysis_service = AnalysisService(
            self.registry
        )

        self.decision_engine = DecisionEngine()

        self.report = ReportBuilder()

        portfolio = PortfolioService(
            self.config.capital_limit
        )

        risk = RiskEngine()

        trading = TradingService()

        trader = PaperTradingEngine(
            portfolio=portfolio,
            risk=risk,
            trading=trading,
        )

        controller = TradingController(
            trader=trader,
        )

        self.trading_runtime = TradingRuntime(
            config=self.config,
            controller=controller,
        )

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

        results = self.analysis_service.analyze(
            "BTC-USD"
        )

        decision = self.decision_engine.evaluate(
            results
        )

        self.report.print_decision(decision)

        self.logger.info("ATLAS is ready.")


if __name__ == "__main__":
    AtlasEngine().start()
