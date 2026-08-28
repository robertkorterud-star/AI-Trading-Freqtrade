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

from atlas.risk.risk_engine import RiskEngine
from atlas.services.portfolio_service import PortfolioService
from atlas.services.technical_service import TechnicalService
from atlas.services.exchange_rate_service import ExchangeRateService
from atlas.trading.paper_trading_engine import PaperTradingEngine
from atlas.trading.trading_controller import TradingController
from atlas.trading.trading_runtime import TradingRuntime
from atlas.trading.trading_service import TradingService
from atlas.trading.prediction_tracker import PredictionTracker
from atlas.trading.outcome_tracker import OutcomeTracker
from pathlib import Path

from atlas.trading.prediction_evaluator import PredictionEvaluator
from atlas.trading.agent_performance_tracker import AgentPerformanceTracker
from atlas.trading.agent_weight_engine import AgentWeightEngine
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
from atlas.adapters.market_data import MarketDataAdapter


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

        self.registry = AgentRegistry()

        self.registry.register(NewsAnalyst(config=self.config))
        self.registry.register(TechnicalAnalyst(config=self.config))
        self.registry.register(CompanyAnalyst(config=self.config))

        self.analysis_service = AnalysisService(
            self.registry
        )

        self.asset_universe = AssetUniverse()

        self.market_data = MarketDataAdapter()

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

        self.technical = TechnicalService()
        self.exchange = ExchangeRateService()

        portfolio = PortfolioService(
            self.config.capital_limit
        )

        risk = RiskEngine()

        trading = TradingService()

        self.prediction_tracker = PredictionTracker(
            storage_path=self.config.database_path
        )

        self.database = Database(
            self.config.database_path
        )

        initialize_database(
            self.database
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
            StrategyMemoryRegimeDecisionAdapter()
        )

        self.analysis_snapshot_repository = (
            AnalysisSnapshotRepository(
                self.database
            )
        )

        self.analysis_snapshot_builder = (
            AnalysisSnapshotBuilder()
        )

        self.outcome_tracker = OutcomeTracker()
        self.outcome_repository = OutcomeRepository(
            self.database
        )

        performance_path = Path(
            self.config.agent_performance_storage
        )

        self.agent_performance = AgentPerformanceTracker(
            storage_path=performance_path
        )

        self.agent_weight_engine = AgentWeightEngine(
            self.agent_performance
        )

        self.decision_engine.agent_weight_engine = (
            self.agent_weight_engine
        )

        self.prediction_evaluator = PredictionEvaluator(
            predictions=self.prediction_tracker,
            outcomes=self.outcome_tracker,
            agent_performance=self.agent_performance,
            outcome_repository=self.outcome_repository,
        )

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
            prediction_tracker=self.prediction_tracker,
        )

    def discover_candidates(
        self,
        limit: int = 3,
        minimum_score: float = 0.0,
    ):
        'Discover and select assets for deeper analysis.'

        discovered = self.asset_discovery.discover(
            self.asset_universe,
        )

        return self.candidate_selector.select(
            discovered,
            limit=limit,
            minimum_score=minimum_score,
        )

    def analyze_candidates(
        self,
        limit: int = 3,
        minimum_score: float = 0.0,
    ):
        """Analyze the selected discovery candidates."""

        candidates = self.discover_candidates(
            limit=limit,
            minimum_score=minimum_score,
        )

        results = []

        for candidate in candidates:
            analysis = self.analysis_service.analyze(
                candidate.symbol
            )

            market_snapshot = self._get_market_snapshot(
                candidate.symbol
            )

            results.append(
                {
                    "symbol": candidate.symbol,
                    "discovery_score": candidate.score,
                    "analysis": analysis,
                    "market_snapshot": market_snapshot,
                }
            )

        return results

    def rank_candidate_decisions(
        self,
        decisions,
        investable_only=False,
        regime_decisions=None,
    ):
        'Rank candidate decisions for portfolio selection.'

        return self.candidate_decision_ranker.rank(
            decisions,
            investable_only=investable_only,
            regime_decisions=regime_decisions,
        )

    def decide_candidates(
        self,
        limit: int = 3,
        minimum_score: float = 0.0,
    ):
        'Create a DecisionResult for each analyzed candidate.'

        analyzed = self.analyze_candidates(
            limit=limit,
            minimum_score=minimum_score,
        )

        results = []

        for item in analyzed:
            decision = self.decision_engine.evaluate(
                item["analysis"]
            )

            regime = getattr(
                item.get("market_snapshot"),
                "regime",
                None,
            )

            regime_decision = None

            if regime:
                regime_decision = (
                    self.get_regime_memory_decision(
                        item["symbol"],
                        regime,
                    )
                )

                decision = self.integrate_regime_decision(
                    decision,
                    regime_decision,
                )

            results.append(
                {
                    "symbol": item["symbol"],
                    "discovery_score": item[
                        "discovery_score"
                    ],
                    "decision": decision,
                    "regime_decision": regime_decision,
                }
            )

        return results

    def integrate_regime_decision(
        self,
        decision,
        regime_decision,
    ):
        """Add strategy-memory regime context to a decision."""

        return self.strategy_memory_decision_integration.integrate(
            decision,
            regime_decision,
        )

    def get_regime_memory_decision(
        self,
        symbol,
        regime,
    ):
        """Build a safe regime-memory decision for a symbol and regime."""

        evidence = (
            self.strategy_memory_regime_evidence_service.analyze(
                symbol=symbol,
                regime=regime,
            )
        )

        recommendation = (
            self.strategy_memory_regime_recommendation_service.recommend(
                evidence
            )
        )

        return self.strategy_memory_regime_decision_adapter.adapt(
            recommendation
        )

    def select_best_candidate(
        self,
        candidates,
        investable_only=False,
    ):
        'Return the strongest candidate decision.'

        if not candidates:
            return None

        decisions = [
            item["decision"]
            for item in candidates
        ]

        regime_decisions = {
            item["symbol"]: item.get("regime_decision")
            for item in candidates
            if item.get("regime_decision") is not None
        }

        ranked_decisions = (
            self.rank_candidate_decisions(
                decisions,
                investable_only=investable_only,
                regime_decisions=regime_decisions,
            )
        )

        if not ranked_decisions:
            return None

        selected_symbol = (
            ranked_decisions[0].symbol
        )

        for item in candidates:
            if item["symbol"] == selected_symbol:
                return item

        return None

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

        evaluation_prices = {}

        for asset in self.asset_universe.all():
            try:
                snapshot = self._get_market_snapshot(
                    asset.symbol
                )
            except Exception:
                continue

            evaluation_prices[asset.symbol] = (
                snapshot.price
            )

        evaluation_results = (
            self.prediction_evaluator.evaluate_ready(
                current_prices_usd=evaluation_prices,
            )
        )

        if evaluation_results:
            self.logger.info(
                f"Evaluated "
                f"{len(evaluation_results)} "
                f"previous prediction(s)."
            )

        candidate_decisions = (
            self.decide_candidates(
                limit=3,
            )
        )

        selected = self.select_best_candidate(
            candidate_decisions,
        )

        if selected is None:
            self.logger.info(
                "No viable candidate found."
            )
            self.logger.info("ATLAS is ready.")
            return

        symbol = selected["symbol"]
        decision = selected["decision"]

        results = [
            result
            for result in selected.get(
                "analysis",
                [],
            )
        ]

        if not results:
            results = self.analysis_service.analyze(
                symbol
            )

        evaluation_snapshot = self._get_market_snapshot(
            symbol
        )

        snapshot = self.analysis_snapshot_builder.build(
            symbol=symbol,
            results=results,
            decision=decision,
            intelligence=(
                self.decision_engine.last_intelligence
            ),
            provider=self.config.ai_provider,
            model="qwen3:4b",
        )

        self.analysis_snapshot_repository.save(
            snapshot
        )

        self.report.print_decision(decision)

        if self.config.trading_mode == "paper":

            snapshot = evaluation_snapshot

            exchange = self._get_usd_nok_rate()

            trade_result = self.trading_runtime.execute(
                decision=decision,
                price_usd=snapshot.price,
                usd_nok=exchange.rate,
                amount_nok=1000.0,
            )

            self.logger.info(
                f"Paper trading result: "
                f"{trade_result}"
            )

        self.logger.info("ATLAS is ready.")

    def _get_market_snapshot(self, symbol):
        return self.technical.get_snapshot(symbol)

    def _get_usd_nok_rate(self):
        return self.exchange.get_rate("USD", "NOK")


if __name__ == "__main__":
    config = build_config_from_args()
    AtlasEngine(config=config).start()
