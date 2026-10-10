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
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult
from atlas.algorithms.position_exit import PositionExitEngine
from atlas.algorithms.regime import MarketRegimeEngine
from atlas.algorithms.pipeline import AlgorithmPipeline
from atlas.algorithms.multi_horizon import HorizonSignal
from atlas.algorithms.registry import AlgorithmRegistry
from atlas.algorithms import (
    IntradayMomentumAlgorithm,
    IntradayTrendAlgorithm,
    IntradayBreakoutAlgorithm,
    IntradayMeanReversionAlgorithm,
    IntradayVWAPAlgorithm,
    IntradayValueZoneAlgorithm,
)

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
from atlas.database.paper_account_state_repository import (
    PaperAccountStateRepository,
)
from atlas.database.event_repository import AtlasEventRepository
from atlas.database.strategy_memory_repository import (
    StrategyMemoryRepository,
)
from atlas.database.analysis_snapshot_repository import (
    AnalysisSnapshotRepository,
)
from atlas.database.asset_repository import AssetRepository
from atlas.services.analysis_snapshot_builder import (
    AnalysisSnapshotBuilder,
)
from atlas.services.dynamic_asset_service import DynamicAssetService
from atlas.services.internet_asset_resolver import InternetAssetResolver
from atlas.services.yfinance_search_client import YFinanceSearchClient

from atlas.market.asset_universe import AssetUniverse
from atlas.market.asset_type import AssetType
from atlas.market.asset_discovery import AssetDiscoveryService
from atlas.market.candidate_selector import CandidateSelector
from atlas.market.trading_horizon import TradingHorizon
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
from atlas.market.candidates.research_tickers import ResearchTickerSource
from atlas.market.candidates.scanner import ScannerCandidateSource
from atlas.services.scanner_service import ScannerService
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

        scanner_exchange = self.config.scanner_exchange.strip().lower()

        if scanner_exchange == "binance":
            from atlas.adapters.binance import BinanceAdapter
            from atlas.adapters.binance_market_data import BinanceMarketData
            from atlas.services.binance_scanner_service import BinanceScannerService

            scanner = BinanceScannerService(
                market_data=BinanceMarketData(
                    adapter=BinanceAdapter(
                        api_key=self.config.binance_api_key,
                    )
                ),
            )
        elif scanner_exchange == "etoro":
            scanner = ScannerService()
        else:
            raise ValueError(
                f"Unsupported scanner exchange: {scanner_exchange}"
            )

        self.scanner_candidate_source = ScannerCandidateSource(
            scanner=scanner,
            exchange=scanner_exchange,
        )

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

        algorithm_registry = AlgorithmRegistry()
        for algorithm in (
            IntradayMomentumAlgorithm(),
            IntradayTrendAlgorithm(),
            IntradayBreakoutAlgorithm(),
            IntradayMeanReversionAlgorithm(),
            IntradayVWAPAlgorithm(),
            IntradayValueZoneAlgorithm(),
        ):
            algorithm_registry.register(algorithm)
        self.algorithm_pipeline = AlgorithmPipeline(algorithm_registry)
        self.market_regime_engine = MarketRegimeEngine()

        self.decision_engine = DecisionEngine(
            trading_cost_model=self.candidate_decision_ranker.cost_model,
        )

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

        self.asset_repository = AssetRepository(
            self.database
        )

        self.asset_universe.add_all(
            self.asset_repository.get_all()
        )

        self.dynamic_asset_service = DynamicAssetService(
            resolver=InternetAssetResolver(YFinanceSearchClient()),
            universe=self.asset_universe,
            repository=self.asset_repository,
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
        self.decision_engine.position_exit_engine = PositionExitEngine(
            accumulation_drop_pct=self.config.accumulation_drop_pct,
        )


        # Persist paper-account peak equity so drawdown survives process restarts.
        self.paper_account_state_repository = PaperAccountStateRepository(
            self.database
        )
        self._peak_equity_nok: float | None = (
            self.paper_account_state_repository.get_peak_equity_nok()
        )

        # Modern execution wiring: pass ExchangeRateService to adapter so
        # it fetches USD/NOK at execute-time (no frozen rate at init).
        paper_adapter = PaperTradingExecutionAdapter(
            portfolio=portfolio,
            trading=trading,
            exchange_service=self.exchange,
            account_state_repository=self.paper_account_state_repository,
        )
        self.paper_execution_adapter = paper_adapter

        self.execution_engine = ExecutionEngine(paper_adapter)
        self.decision_execution_service = DecisionExecutionService(self.execution_engine)

        # The paper adapter restores positions from persisted trades. Reconcile
        # durable per-position state only after that reconstruction is complete.
        self._reconcile_position_peak_state()

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

    @property
    def market_data(self):
        return self._market_data

    @market_data.setter
    def market_data(self, value):
        self._market_data = value

        if hasattr(self, "technical"):
            self.technical.market = value

        if hasattr(self, "registry"):
            technical_analyst = self.registry.get("Technical Analyst")
            if technical_analyst is not None:
                technical_analyst.market = value


    def research_candidates(
        self,
        research: str = "",
        limit: int = 10,
        minimum_score: float = 0.0,
        horizon: TradingHorizon | None = None,
    ):
        """Discover research candidates using AI and market discovery."""

        ai_research = research
        research_context = None

        if not ai_research.strip():
            research_context = self.candidate_research_service.get_context(
                limit=limit,
            )
            ai_research = research_context.as_text()

        ai_provider = AIProviderFactory.create(
            config=self.config,
        )

        ai_candidates = AIResearchSource(
            AICandidateProvider(ai_provider),
            research=ai_research,
        )

        market_candidates = MarketDiscoverySource(
            discovery=self.asset_discovery,
            universe=self.asset_universe,
            limit=limit,
            minimum_score=minimum_score,
            horizon=horizon,
        )

        sources = [
            ai_candidates,
            market_candidates,
        ]

        scanner_candidate_source = getattr(
            self,
            "scanner_candidate_source",
            None,
        )
        if scanner_candidate_source is not None:
            sources.append(scanner_candidate_source)

        if research_context is not None:
            sources.append(
                ResearchTickerSource(
                    research_context.articles,
                )
            )

        pool = CandidatePool(
            sources=sources,
        )

        return pool.collect()[:max(0, limit)]

    def expand_universe_from_candidates(self, candidates):
        """Resolve researched candidates into the active asset universe."""
        added = 0

        for candidate in candidates:
            if self.asset_universe.get(candidate.symbol) is not None:
                continue
            added += int(
                self.dynamic_asset_service.resolve_and_add_symbol(candidate.symbol)
            )

        return added

    def discover_candidates(
        self,
        limit: int = 3,
        minimum_score: float = 0.0,
        horizon: TradingHorizon | None = None,
        trigger_symbol: str | None = None,
    ):
        'Discover and select assets for deeper analysis.'

        if horizon is None:
            discovered = self.asset_discovery.discover(
                self.asset_universe,
            )
        else:
            discovered = self.asset_discovery.discover(
                self.asset_universe,
                horizon=horizon,
            )

        selector_kwargs = {
            "limit": limit,
            "minimum_score": minimum_score,
        }
        if trigger_symbol is not None:
            selector_kwargs["trigger_symbol"] = trigger_symbol

        return self.candidate_selector.select(
            discovered,
            **selector_kwargs,
        )

    def analyze_candidates(
        self,
        limit: int = 3,
        minimum_score: float = 0.0,
        horizon: TradingHorizon | None = None,
        trigger_symbol: str | None = None,
    ):
        """Analyze the selected discovery candidates."""

        if horizon is None:
            if trigger_symbol is None:
                candidates = self.discover_candidates(
                    limit=limit,
                    minimum_score=minimum_score,
                )
            else:
                candidates = self.discover_candidates(
                    limit=limit,
                    minimum_score=minimum_score,
                    trigger_symbol=trigger_symbol,
                )
        else:
            if trigger_symbol is None:
                candidates = self.discover_candidates(
                    limit=limit,
                    minimum_score=minimum_score,
                    horizon=horizon,
                )
            else:
                candidates = self.discover_candidates(
                    limit=limit,
                    minimum_score=minimum_score,
                    horizon=horizon,
                    trigger_symbol=trigger_symbol,
                )

        results = []

        for candidate in candidates:
            exclude = None
            if candidate.asset.asset_type is AssetType.CRYPTO:
                exclude = {"Company Analyst"}

            analysis = self.analysis_service.analyze(
                candidate.symbol,
                exclude=exclude,
            )

            algorithm_signals = None
            fusion_result = None
            horizon_signal = None
            market_regime = None
            if getattr(candidate, "asset", None) is not None:
                if horizon is None:
                    normalized_snapshot = self.market_data.snapshot(
                        candidate.symbol,
                        interval="5m",
                        limit=100,
                    )
                else:
                    normalized_snapshot = self.market_data.snapshot_for_horizon(
                        candidate.symbol,
                        horizon,
                        limit=100,
                    )
                fusion_result, algorithm_signals = self.algorithm_pipeline.analyze(
                    candidate.symbol,
                    normalized_snapshot,
                )
                if horizon is not None:
                    if fusion_result is not None:
                        horizon_signal = HorizonSignal.from_fusion(
                            horizon,
                            fusion_result,
                        )
                    elif hasattr(normalized_snapshot, "candles"):
                        horizon_signal = HorizonSignal.from_candles(
                            horizon,
                            normalized_snapshot.candles,
                        )
                if (
                    hasattr(self, "market_regime_engine")
                    and hasattr(normalized_snapshot, "candles")
                ):
                    market_regime = self.market_regime_engine.analyze(
                        candidate.symbol,
                        list(normalized_snapshot.candles),
                    )

            market_snapshot = self._get_market_snapshot(
                candidate.symbol
            )

            results.append(
                {
                    "symbol": candidate.symbol,
                    "discovery_score": candidate.score,
                    "discovery_input": getattr(
                        candidate,
                        "discovery_input",
                        None,
                    ),
                    "horizon": getattr(
                        candidate,
                        "horizon",
                        None,
                    ),
                    "analysis": analysis,
                    "algorithm_signals": algorithm_signals,
                    "fusion_result": fusion_result,
                    "horizon_signal": horizon_signal,
                    "market_regime": market_regime,
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

    def rank_candidate_decisions_with_evidence(
        self,
        candidates,
        investable_only=False,
    ):
        """Return candidate ranking evidence in ranking order."""

        if not candidates:
            return []

        decisions = [
            item["decision"]
            for item in candidates
        ]

        regime_decisions = {
            item["symbol"]: item.get("regime_decision")
            for item in candidates
            if item.get("regime_decision") is not None
        }

        return self.candidate_decision_ranker.rank_with_evidence(
            decisions,
            investable_only=investable_only,
            regime_decisions=regime_decisions,
        )

    def decide_candidates(
        self,
        limit: int = 3,
        minimum_score: float = 0.0,
        horizon: TradingHorizon | None = None,
        trigger_symbol: str | None = None,
    ):
        'Create a DecisionResult for each analyzed candidate.'

        if horizon is None:
            if trigger_symbol is None:
                analyzed = self.analyze_candidates(
                    limit=limit,
                    minimum_score=minimum_score,
                )
            else:
                analyzed = self.analyze_candidates(
                    limit=limit,
                    minimum_score=minimum_score,
                    trigger_symbol=trigger_symbol,
                )
        else:
            if trigger_symbol is None:
                analyzed = self.analyze_candidates(
                    limit=limit,
                    minimum_score=minimum_score,
                    horizon=horizon,
                )
            else:
                analyzed = self.analyze_candidates(
                    limit=limit,
                    minimum_score=minimum_score,
                    horizon=horizon,
                    trigger_symbol=trigger_symbol,
                )

        results = []

        for item in analyzed:
            decision = self._evaluate_candidate_decision(
                item["analysis"],
                market_snapshot=item.get("market_snapshot"),
                algorithm_signals=item.get("algorithm_signals"),
                fusion_result=item.get("fusion_result"),
                horizon_signal=item.get("horizon_signal"),
            )

            market_regime = item.get("market_regime")
            regime = getattr(
                market_regime,
                "regime",
                None,
            )
            if regime is None:
                regime = getattr(
                    item.get("market_snapshot"),
                    "regime",
                    None,
                )
            if hasattr(regime, "value"):
                regime = regime.value

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
                    "discovery_input": item.get(
                        "discovery_input"
                    ),
                    "horizon": item.get(
                        "horizon"
                    ),
                    "analysis": item.get(
                        "analysis"
                    ),
                    "algorithm_signals": item.get(
                        "algorithm_signals"
                    ),
                    "fusion_result": item.get(
                        "fusion_result"
                    ),
                    "horizon_signal": item.get(
                        "horizon_signal"
                    ),
                    "market_snapshot": item.get(
                        "market_snapshot"
                    ),
                    "market_regime": market_regime,
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
        economically_eligible_only=False,
    ):
        'Return the strongest candidate decision.'

        if not candidates:
            return None

        if economically_eligible_only:
            candidates = [
                item
                for item in candidates
                if self.candidate_decision_ranker.is_economically_eligible(
                    item["decision"]
                )
            ]

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

        ranked_evidence = (
            self.rank_candidate_decisions_with_evidence(
                candidates,
                investable_only=investable_only,
            )
        )

        selected_symbol = (
            ranked_decisions[0].symbol
        )

        selected_evidence = None

        for evidence in ranked_evidence:
            if evidence.symbol == selected_symbol:
                selected_evidence = evidence
                break

        for item in candidates:
            if item["symbol"] == selected_symbol:
                item = dict(item)

                if selected_evidence is not None:
                    item["ranking_evidence"] = (
                        selected_evidence
                    )

                    item["selection_report"] = (
                        CandidateSelectionReport(
                            symbol=selected_symbol,
                            action=str(
                                item["decision"].action.value
                                if hasattr(
                                    item["decision"].action,
                                    "value",
                                )
                                else item["decision"].action
                            ),
                            ranking_evidence=(
                                selected_evidence
                            ),
                        )
                    )

                    self.logger.info(
                        "ATLAS candidate selected: "
                        f"{selected_symbol}"
                    )

                    for line in (
                        item["selection_report"].reasoning
                    ):
                        self.logger.info(
                            f"ATLAS selection evidence: {line}"
                        )

                return item

        return None

    def get_candidate_selection_report(
        self,
        candidates,
        investable_only=False,
    ):
        """Return the explainable report for the selected candidate."""

        selected = self.select_best_candidate(
            candidates,
            investable_only=investable_only,
        )

        if selected is None:
            return None

        return selected.get(
            "selection_report"
        )

    def get_candidate_selection_snapshot(
        self,
        candidates,
        investable_only=False,
    ):
        """Return the machine-readable snapshot for the selected candidate."""

        report = self.get_candidate_selection_report(
            candidates,
            investable_only=investable_only,
        )

        if report is None:
            return None

        return report.selection_snapshot

    def start(
        self,
        trigger_symbol: str | None = None,
    ):

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
            self.event_repository.publish(
                "LEARNING_UPDATED",
                {"evaluated_predictions": len(evaluation_results)},
            )

        if trigger_symbol is None:
            candidate_decisions = self.decide_candidates(
                limit=3,
            )
        else:
            candidate_decisions = self.decide_candidates(
                limit=3,
                trigger_symbol=trigger_symbol,
            )

        selected = self.select_best_candidate(
            candidate_decisions,
        )

        if selected is not None:
            selection_report = selected.get(
                "selection_report"
            )

            if selection_report is not None:
                self.logger.info(
                    "ATLAS selection report ready for "
                    f"{selected['symbol']}."
                )

                selection_snapshot = (
                    selection_report.selection_snapshot
                )

                self.logger.info(
                    "ATLAS selection snapshot: "
                    f"{json.dumps(selection_snapshot, ensure_ascii=False, sort_keys=True)}"
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

        fusion_result = selected.get(
            "fusion_result"
        )
        algorithm_signals = selected.get(
            "algorithm_signals"
        )

        if fusion_result is not None:
            results = list(results)
            results.append(
                DecisionEngine._fusion_result_to_analysis(
                    fusion_result
                )
            )
        elif algorithm_signals:
            results = list(results)
            results.extend(
                DecisionEngine._algorithm_signal_to_analysis(
                    signal
                )
                for signal in algorithm_signals
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

        self.event_repository.publish(
            "DECISION_READY",
            {
                "symbol": symbol,
                "action": str(getattr(decision.action, "value", decision.action)),
                "confidence": getattr(decision, "confidence", None),
                "analysis_snapshot_id": getattr(snapshot, "database_id", None),
            },
        )

        self.report.print_decision(decision)

        self.prediction_tracker.record(
            decision=decision,
            price_usd=evaluation_snapshot.price,
            reason="ATLAS prediction.",
        )

        if self.config.paper_trading:

            snapshot = evaluation_snapshot

            # Use the modern DecisionExecutionService as the production execution path.
            # DecisionEngine must already have produced risk_assessment and portfolio_assessment.
            exec_result = self.decision_execution_service.execute(
                decision,
                price=snapshot.price,
                analysis_snapshot_id=getattr(
                    decision,
                    "analysis_snapshot_id",
                    None,
                ),
            )

            if exec_result is not None:
                usd_nok = self._get_usd_nok_rate().rate
                self._sync_position_peak_after_execution(
                    symbol=symbol,
                    action=decision.action,
                    usd_nok=usd_nok,
                )

                self.event_repository.publish(
                    "TRADE_EXECUTED",
                    {
                        "symbol": symbol,
                        "action": str(getattr(decision.action, "value", decision.action)),
                        "quantity": (
                            exec_result.get("quantity")
                            if isinstance(exec_result, dict)
                            else getattr(exec_result, "quantity", None)
                        ),
                        "analysis_snapshot_id": getattr(decision, "analysis_snapshot_id", None),
                    },
                )

            self.logger.info(
                f"Paper trading result: {exec_result}"
            )

        self.logger.info("ATLAS is ready.")


    def _get_market_snapshot(self, symbol):
        return self.technical.get_snapshot(symbol)

    def _get_usd_nok_rate(self):
        return self.exchange.get_rate("USD", "NOK")

    @property
    def exchange(self):
        if not hasattr(self, "_exchange"):
            self._exchange = ExchangeRateService()
        return self._exchange

    @exchange.setter
    def exchange(self, value):
        self._exchange = value

    def _sync_position_peak_after_execution(
        self,
        *,
        symbol,
        action,
        usd_nok,
    ):
        """Synchronize durable position peak after paper execution."""
        if action is not Action.SELL:
            return

        portfolio_snapshot = self.portfolio_service.as_dict(usd_nok)
        still_open = any(
            position.get("symbol") == symbol
            for position in portfolio_snapshot.get("positions", [])
        )
        if not still_open:
            self.paper_account_state_repository.delete_position_peak_price_usd(
                symbol
            )

    def _reconcile_position_peak_state(self):
        """Reconcile durable peaks with the canonical open-position set."""
        open_position_symbols = set(
            self.portfolio_service._positions
        )

        for persisted_symbol in (
            self.paper_account_state_repository
            .get_position_peak_symbols()
        ):
            if persisted_symbol not in open_position_symbols:
                self.paper_account_state_repository.delete_position_peak_price_usd(
                    persisted_symbol
                )

        for position in self.portfolio_service._positions.values():
            persisted_peak = (
                self.paper_account_state_repository
                .get_position_peak_price_usd(position.symbol)
            )
            if persisted_peak is not None:
                position.peak_price_usd = max(
                    position.peak_price_usd,
                    persisted_peak,
                )

    def restore_paper_portfolio(self):
        """Restore paper positions and durable per-position state."""
        self.paper_execution_adapter.restore_portfolio()
        self._reconcile_position_peak_state()

    def _evaluate_candidate_decision(
        self,
        analysis,
        *,
        market_snapshot=None,
        algorithm_signals=None,
        fusion_result=None,
        horizon_signal=None,
    ):
        """Invoke `DecisionEngine.evaluate` with combined evidence and runtime context."""
        combined_analysis = analysis
        if fusion_result is not None:
            combined_analysis = list(analysis)
            combined_analysis.append(
                DecisionEngine._fusion_result_to_analysis(fusion_result)
            )
        elif algorithm_signals:
            combined_analysis = list(analysis)
            combined_analysis.extend(
                DecisionEngine._algorithm_signal_to_analysis(signal)
                for signal in algorithm_signals
            )

        if horizon_signal is not None and fusion_result is None:
            combined_analysis = list(combined_analysis)
            combined_analysis.append(
                AnalysisResult(
                    analyst=f"horizon:{horizon_signal.horizon.value}",
                    symbol=combined_analysis[0].symbol,
                    action=horizon_signal.action,
                    confidence=horizon_signal.confidence,
                    evidence=max(
                        0.0,
                        min(
                            100.0,
                            abs(float(horizon_signal.score) - 50.0) * 2.0,
                        ),
                    ),
                    signal_confidence=horizon_signal.confidence,
                    metadata={
                        "horizon": horizon_signal.horizon.value,
                        "score": horizon_signal.score,
                    },
                )
            )

        params = inspect.signature(self.decision_engine.evaluate).parameters
        kwargs = {}
        runtime_context = None

        def get_runtime_context():
            nonlocal runtime_context
            if runtime_context is None:
                exchange = self._get_usd_nok_rate()
                usd_nok = float(exchange.rate)
                if usd_nok <= 0.0:
                    raise RuntimeError("Invalid USD/NOK rate from ExchangeRateService")
                prices = {}
                if (
                    market_snapshot is not None
                    and getattr(market_snapshot, "price", None) is not None
                ):
                    prices[combined_analysis[0].symbol] = float(
                        market_snapshot.price
                    )

                portfolio_snapshot = self.portfolio_service.as_dict(
                    usd_nok
                )
                open_symbols = [
                    position.get("symbol")
                    for position in portfolio_snapshot.get("positions", [])
                    if position.get("symbol")
                    and position.get("symbol") not in prices
                ]
                if open_symbols and hasattr(self.market_data, "get_many"):
                    market_prices = self.market_data.get_many(open_symbols)
                    for symbol, snapshot in market_prices.items():
                        price = getattr(snapshot, "price", None)
                        if price is not None:
                            prices[symbol] = float(price)

                if prices:
                    self.portfolio_service.update_prices(prices)

                updated_portfolio_snapshot = self.portfolio_service.as_dict(
                    usd_nok
                )
                if hasattr(self, "paper_account_state_repository"):
                    for position in updated_portfolio_snapshot.get(
                        "positions", []
                    ):
                        symbol = position.get("symbol")
                        peak_price_usd = position.get("peak_price_usd")
                        if not symbol or peak_price_usd is None:
                            continue
                        persisted_peak = (
                            self.paper_account_state_repository
                            .get_position_peak_price_usd(symbol)
                        )
                        if (
                            persisted_peak is None
                            or float(peak_price_usd) > persisted_peak
                        ):
                            self.paper_account_state_repository.set_position_peak_price_usd(
                                symbol,
                                float(peak_price_usd),
                            )

                runtime_context = (
                    usd_nok,
                    updated_portfolio_snapshot,
                )
            return runtime_context

        if "price" in params:
            kwargs["price"] = getattr(market_snapshot, "price", None)
        if "equity" in params:
            usd_nok, portfolio_snapshot = get_runtime_context()
            total_equity_nok = float(portfolio_snapshot.get("total_equity_nok", 0.0))
            kwargs["equity"] = total_equity_nok / usd_nok
        if "current_exposure_pct" in params:
            _, portfolio_snapshot = get_runtime_context()
            total_equity_nok = float(portfolio_snapshot.get("total_equity_nok", 0.0))
            positions_value_nok = float(portfolio_snapshot.get("positions_value_nok", 0.0))
            current_exposure_pct = (
                (positions_value_nok / total_equity_nok * 100.0)
                if total_equity_nok and total_equity_nok > 0.0
                else 0.0
            )
            kwargs["current_exposure_pct"] = current_exposure_pct
        if "drawdown_pct" in params:
            _, portfolio_snapshot = get_runtime_context()
            total_equity_nok = float(portfolio_snapshot.get("total_equity_nok", 0.0))
            persisted_peak = None
            if self._peak_equity_nok is None and hasattr(
                self, "paper_account_state_repository"
            ):
                persisted_peak = (
                    self.paper_account_state_repository.get_peak_equity_nok()
                )
            previous_peak = (
                self._peak_equity_nok
                if self._peak_equity_nok is not None
                else persisted_peak
            )
            self._peak_equity_nok = max(
                previous_peak if previous_peak is not None else total_equity_nok,
                total_equity_nok,
            )
            if (
                previous_peak is None
                or self._peak_equity_nok > previous_peak
            ) and hasattr(self, "paper_account_state_repository"):
                self.paper_account_state_repository.set_peak_equity_nok(
                    self._peak_equity_nok
                )
            drawdown_pct = (
                max(0.0, (self._peak_equity_nok - total_equity_nok) / self._peak_equity_nok * 100.0)
                if self._peak_equity_nok and self._peak_equity_nok > 0.0
                else 0.0
            )
            kwargs["drawdown_pct"] = drawdown_pct
        if "portfolio_positions" in params:
            usd_nok, portfolio_snapshot = get_runtime_context()
            portfolio_positions = []
            for p in portfolio_snapshot.get("positions", []):
                try:
                    mv_nok = float(p.get("market_value_nok", 0.0))
                except Exception:
                    mv_nok = 0.0
                market_value_usd = mv_nok / usd_nok if usd_nok else 0.0
                portfolio_positions.append(PortfolioPosition(symbol=p.get("symbol", ""), market_value=market_value_usd))
            kwargs["portfolio_positions"] = portfolio_positions
        if (
            "current_position" in params
            or "last_buy_price" in params
            or "average_price" in params
            or "peak_price" in params
        ):
            _, portfolio_snapshot = get_runtime_context()
            for p in portfolio_snapshot.get("positions", []):
                if p.get("symbol") != combined_analysis[0].symbol:
                    continue
                if "current_position" in params:
                    kwargs["current_position"] = float(p.get("quantity", 0.0))
                if "last_buy_price" in params:
                    kwargs["last_buy_price"] = p.get("last_buy_price_usd")
                if "average_price" in params:
                    kwargs["average_price"] = p.get("average_price_usd")
                if "peak_price" in params:
                    kwargs["peak_price"] = p.get("peak_price_usd")
                break

        if kwargs:
            return self.decision_engine.evaluate(combined_analysis, **kwargs)
        return self.decision_engine.evaluate(combined_analysis)


if __name__ == "__main__":
    config = build_config_from_args()
    AtlasEngine(config=config).start()
