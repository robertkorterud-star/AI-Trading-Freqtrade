"""
ATLAS Engine
"""

from atlas.agents.technical_analyst import TechnicalAnalyst
from atlas.agents.company_analyst import CompanyAnalyst
from atlas.core.config import AtlasConfig
from atlas.core.logger import get_logger
from atlas.core.registry import AgentRegistry
from atlas.core.analysis_service import AnalysisService

from atlas.agents.news_analyst import NewsAnalyst

from atlas.decision.engine import DecisionEngine

from atlas.report.report_builder import ReportBuilder

from atlas.services.portfolio_service import PortfolioService
from atlas.services.technical_service import TechnicalService
from atlas.services.exchange_rate_service import ExchangeRateService
from atlas.trading.trading_service import TradingService
from atlas.risk.manager import RiskManager
from atlas.portfolio.manager import PortfolioManager
from atlas.portfolio.manager import PortfolioPosition
from atlas.execution.service import DecisionExecutionService
from atlas.execution.protocol import ExecutionEngine
from atlas.execution.paper_adapter import PaperTradingExecutionAdapter
from atlas.trading.prediction_tracker import PredictionTracker
from atlas.trading.outcome_tracker import OutcomeTracker
from pathlib import Path
import json
import inspect

from atlas.trading.prediction_evaluator import PredictionEvaluator
from atlas.trading.agent_performance_tracker import AgentPerformanceTracker
from atlas.trading.agent_weight_engine import AgentWeightEngine
from atlas.trading.expected_return_service import ExpectedReturnService
from atlas.trading.historical_return_provider import HistoricalReturnProvider
from atlas.trading.strategy_memory_regime_decision_integration import (
    StrategyMemoryRegimeDecisionIntegration,
)
from atlas.trading.strategy_memory_regime_evidence_service import (
    StrategyMemoryRegimeEvidenceService,
)
from atlas.trading.strategy_memory_regime_recommendation_service import (
    StrategyMemoryRegimeRecommendationService,
)
from atlas.trading.strategy_memory_regime_decision_adapter import (
    StrategyMemoryRegimeDecisionAdapter,
)

from atlas.database.connection import Database
from atlas.database.schema import initialize_database
from atlas.database.outcome_repository import OutcomeRepository
from atlas.database.prediction_repository import PredictionRepository
from atlas.database.trade_repository import TradeRepository
from atlas.database.event_repository import AtlasEventRepository
from atlas.database.strategy_memory_repository import (
    StrategyMemoryRepository,
)
from atlas.database.analysis_snapshot_repository import (
    AnalysisSnapshotRepository,
)
from atlas.services.analysis_snapshot_builder import (
    AnalysisSnapshotBuilder,
)

from atlas.market.asset_universe import AssetUniverse
from atlas.market.asset_discovery import AssetDiscoveryService
from atlas.market.candidate_selector import CandidateSelector
from atlas.market.candidate_decision_ranker import (
    CandidateDecisionRanker,
)
from atlas.market.candidate_selection_report import (
    CandidateSelectionReport,
)
from atlas.adapters.market_data import MarketDataAdapter
from atlas.market.candidates.source import CandidatePool
from atlas.market.candidates.ai_research import AIResearchSource
from atlas.market.candidates.ai_provider import AICandidateProvider
from atlas.market.candidates.market_discovery import MarketDiscoverySource
from atlas.market.candidates.research_service import CandidateResearchService
from atlas.core.ai_provider_factory import AIProviderFactory


def build_config_from_args(args=None):
    """Build ATLAS configuration from command-line arguments."""

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--paper",
        action="store_true",
        help="Run ATLAS in paper/dry-run mode.",
    )

    parsed = parser.parse_args(args)

    if parsed.paper:
        return AtlasConfig(
            trading_mode="paper",
            paper_trading=True,
        )

    return AtlasConfig()


class AtlasEngine:
    """Main entry point for ATLAS."""

    def __init__(self, config=None):

        self.config = config or AtlasConfig()

        self.logger = get_logger("ATLAS")

        self.market_data = MarketDataAdapter()

        self.candidate_research_service = CandidateResearchService()

        self.registry = AgentRegistry()

        self.registry.register(NewsAnalyst(config=self.config))
        self.registry.register(
            TechnicalAnalyst(
                config=self.config,
                market_data=self.market_data,
            )
        )
        self.registry.register(CompanyAnalyst(config=self.config))

        self.analysis_service = AnalysisService(
            self.registry
        )

        self.asset_universe = AssetUniverse()

        self.asset_discovery = AssetDiscoveryService(
            market_data=self.market_data,
        )

        self.candidate_selector = CandidateSelector()

        self.candidate_decision_ranker = (
            CandidateDecisionRanker()
        )

        self.decision_engine = DecisionEngine()

        self.strategy_memory_decision_integration = (
            StrategyMemoryRegimeDecisionIntegration()
        )

        self.report = ReportBuilder()

        self.technical = TechnicalService(
            market_data=self.market_data
        )

        portfolio = PortfolioService(
            self.config.capital_limit
        )

        self.database = Database(
            self.config.database_path
        )

        initialize_database(
            self.database
        )

        # Expose service instances for testability and adapter wiring.
        self.portfolio_service = portfolio

        trade_repository = TradeRepository(
            self.database
        )
        trading = TradingService(
            repository=trade_repository
        )

        # Expose trading service used by the paper adapter for tests and inspection
        self.trading_service = trading

        # State-change events are persisted in the same SQLite database so the
        # dashboard can observe ATLAS even when it runs in another process.
        self.event_repository = AtlasEventRepository(
            self.database
        )

        # Modern risk and portfolio managers (do not replace legacy services)
        portfolio_manager = PortfolioManager()
        risk_manager = RiskManager()

        # Expose modern managers on the engine for controlled usage.
        # We intentionally do not assign them onto `DecisionEngine` here to
        # preserve existing code paths that expect `DecisionEngine` to be
        # usable without price/equity being supplied.
        self.risk_manager = risk_manager
        self.portfolio_manager = portfolio_manager
        # Make DecisionEngine the canonical owner of the modern managers so
        # that DecisionEngine itself will produce risk/portfolio assessments
        # during `evaluate()` when supplied with the runtime context.
        self.decision_engine.risk_manager = risk_manager
        self.decision_engine.portfolio_manager = portfolio_manager


        # Track peak equity in NOK for drawdown calculation (mirror DryRunLoop)
        self._peak_equity_nok: float | None = None

        # Modern execution wiring: pass ExchangeRateService to adapter so
        # it fetches USD/NOK at execute-time (no frozen rate at init).
        paper_adapter = PaperTradingExecutionAdapter(
            portfolio=portfolio,
            trading=trading,
            exchange_service=self.exchange,
            accumulation_drop_pct=self.config.accumulation_drop_pct,
        )

        self.execution_engine = ExecutionEngine(paper_adapter)
        self.decision_execution_service = DecisionExecutionService(self.execution_engine)

        self.prediction_tracker = PredictionTracker(
            storage_path=self.config.database_path
        )

        self.prediction_repository = PredictionRepository(
            self.database
        )

        self.historical_return_provider = HistoricalReturnProvider(
            repository=self.prediction_repository
        )

        self.expected_return_service = ExpectedReturnService(
            provider=self.historical_return_provider
        )

        self.decision_engine.expected_return_service = (
            self.expected_return_service
        )

        self.strategy_memory_repository = (
            StrategyMemoryRepository(
                self.database
            )
        )

        self.strategy_memory_regime_evidence_service = (
            StrategyMemoryRegimeEvidenceService(
                repository=self.strategy_memory_repository
            )
        )

        self.strategy_memory_regime_recommendation_service = (
            StrategyMemoryRegimeRecommendationService()
        )

        self.strategy_memory_regime_decision_adapter = (
            StrategyMemoryRegimeDecisionAdapter(
                recommendation_service=self.strategy_memory_regime_recommendation_service,
            )
        )
