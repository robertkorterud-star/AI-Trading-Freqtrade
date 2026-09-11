"""
Dashboard Data Service

Collects all data required by the dashboard from canonical ATLAS state.
"""

import time

from atlas.config.settings import settings
from atlas.core.config import AtlasConfig
from atlas.core.registry import AgentRegistry
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult
from atlas.models.decision_result import DecisionResult
from atlas.models.intelligence_summary import IntelligenceSummary
from atlas.agents.news_analyst import NewsAnalyst
from atlas.agents.technical_analyst import TechnicalAnalyst
from atlas.agents.company_analyst import CompanyAnalyst
from atlas.decision.explanation import explain_decision
from atlas.services.exchange_rate_service import ExchangeRateService
from atlas.services.portfolio_service import PortfolioService
from atlas.services.settings_service import SettingsService
from atlas.trading.trading_service import TradingService
from atlas.trading.agent_performance_tracker import AgentPerformanceTracker
from atlas.trading.agent_weight_engine import AgentWeightEngine
from atlas.database.connection import Database
from atlas.database.schema import initialize_database
from atlas.database.analysis_snapshot_repository import AnalysisSnapshotRepository
from atlas.database.prediction_repository import PredictionRepository
from atlas.market.asset_universe import AssetUniverse
from atlas.market.asset_discovery import AssetDiscoveryService
from atlas.adapters.market_data import MarketDataAdapter
from atlas.adapters.intelligence_sources import IntelligenceSourceAdapter
from atlas.market.candidate_decision_ranker import CandidateDecisionRanker


class DashboardDataService:
    """Collect dashboard data without creating a second decision path."""

    def __init__(self, config=None, intelligence_sources=None):
        self.config = config or AtlasConfig()
        self.settings = SettingsService(config=self.config)
        self.registry = AgentRegistry()
        self.registry.register(NewsAnalyst(config=self.config))
        self.registry.register(TechnicalAnalyst())
        self.registry.register(CompanyAnalyst())
        self.exchange = ExchangeRateService()
        self.portfolio = PortfolioService()
        self.trading = TradingService()
        self.asset_universe = AssetUniverse()
        self.market_data = MarketDataAdapter()
        self.intelligence_sources = intelligence_sources
        self._news_cache = {}
        self._news_cache_ttl_seconds = 300.0
        self.asset_discovery = AssetDiscoveryService(market_data=self.market_data)
        self.candidate_decision_ranker = CandidateDecisionRanker()
        database = Database(self.config.database_path)
        initialize_database(database)
        self.snapshot_repository = AnalysisSnapshotRepository(database)
        self.prediction_repository = PredictionRepository(database)
        self.agent_performance = AgentPerformanceTracker(storage_path=self.config.agent_performance_storage)
        has_performance_history = any(item["predictions"] > 0 for item in self.agent_performance.history())
        if not has_performance_history:
            evaluated_predictions = self.prediction_repository.get_evaluated()
            if evaluated_predictions:
                self.agent_performance.rebuild_from_predictions(evaluated_predictions)
        self.agent_weight_engine = AgentWeightEngine(self.agent_performance)
        for agent in self.registry.get_all():
            self.agent_performance.ensure(agent.name)

    @staticmethod
    def _snapshot_results(snapshot):
        """Rebuild AnalysisResult objects from a canonical snapshot."""
        return [
            AnalysisResult(
                analyst=result["analyst"],
                symbol=result["symbol"],
                action=Action(result["action"]),
                confidence=float(result["confidence"]),
                evidence=float(result["evidence"]),
                reasoning=list(result.get("reasoning", [])),
            )
            for result in snapshot.results
        ]

    @staticmethod
    def _snapshot_decision(snapshot):
        """Rebuild DecisionResult from a canonical snapshot."""
        data = snapshot.decision
        dominant_action = data.get("dominant_action")
        return DecisionResult(
            symbol=data["symbol"],
            action=Action(data["action"]),
            confidence=float(data["confidence"]),
            evidence=float(data["evidence"]),
            analysts=list(data.get("analysts", [])),
            agent_weights=dict(data.get("agent_weights", {})),
            dominant_action=Action(dominant_action) if dominant_action else None,
            dominant_weight=float(data.get("dominant_weight", 0.0)),
            action_support_analyst=data.get("action_support_analyst"),
            action_support_action=Action(data["action_support_action"]) if data.get("action_support_action") else None,
            action_support_weight=float(data.get("action_support_weight", 0.0)),
            opposing_analysts=list(data.get("opposing_analysts", [])),
            adaptive_override=bool(data.get("adaptive_override", False)),
            decision_margin=float(data.get("decision_margin", 0.0)),
            robustness=float(data.get("robustness", 0.0)),
            robustness_level=data.get("robustness_level", "WEAK"),
            reasoning=list(data.get("reasoning", [])),
        )

    @staticmethod
    def _snapshot_intelligence(snapshot):
        """Rebuild IntelligenceSummary from a canonical snapshot."""
        data = snapshot.intelligence
        return IntelligenceSummary(
            symbol=data["symbol"],
            action=Action(data["action"]),
            evidence=float(data["evidence"]),
            confidence=float(data["confidence"]),
            buy_count=int(data["buy_count"]),
            hold_count=int(data["hold_count"]),
            sell_count=int(data["sell_count"]),
            agreement=float(data["agreement"]),
            conflict=bool(data["conflict"]),
            weighted_buy=float(data.get("weighted_buy", 0.0)),
            weighted_hold=float(data.get("weighted_hold", 0.0)),
            weighted_sell=float(data.get("weighted_sell", 0.0)),
            weighted_agreement=float(data.get("weighted_agreement", 0.0)),
            weighted_conflict=bool(data.get("weighted_conflict", False)),
            analysts=list(data.get("analysts", [])),
            reasoning=list(data.get("reasoning", [])),
        )

    def market_scan(self, limit=5):
        """Rank only decisions already produced by the canonical runtime."""
        try:
            discovered = self.asset_discovery.discover(self.asset_universe, limit=limit)
        except Exception:
            discovered = []
        candidates = []
        for item in discovered:
            snapshot = self.snapshot_repository.get_latest_valid(item.symbol)
            if snapshot is None:
                continue
            decision = self._snapshot_decision(snapshot)
            candidates.append({"symbol": item.symbol, "discovery_score": round(item.score, 1), "decision": decision})
        ranked = self.candidate_decision_ranker.rank([item["decision"] for item in candidates])
        selected_symbol = ranked[0].symbol if ranked else None
        by_symbol = {item["symbol"]: item for item in candidates}
        return [
            {
                "symbol": decision.symbol,
                "discovery_score": by_symbol[decision.symbol]["discovery_score"],
                "decision": decision.action.value,
                "confidence": round(decision.confidence, 1),
                "selected": decision.symbol == selected_symbol,
            }
            for decision in ranked
        ]

    def _get_latest_news(self, symbol):
        """Return cached external intelligence for dashboard news context."""
        now = time.monotonic()
        cached = self._news_cache.get(symbol)

        if cached is not None:
            created_at, result = cached
            if now - created_at < self._news_cache_ttl_seconds:
                return result

        try:
            if self.intelligence_sources is None:
                self.intelligence_sources = IntelligenceSourceAdapter()
            result = self.intelligence_sources.get(symbol)
        except Exception:
            result = []

        if not isinstance(result, list):
            result = []

        self._news_cache[symbol] = (now, result)
        return result

    def get_dashboard_data(self, selected_symbol=None):
        default_watchlist = ["BTC-USD", "ETH-USD", "SOL-USD", "NVDA"]
        selected_symbol = (selected_symbol or settings.default_symbol).strip().upper()
        watchlist = [selected_symbol] + [symbol for symbol in default_watchlist if symbol != selected_symbol]

        exchange = self.exchange.get_rate("USD", "NOK")
        market = []
        latest_results = None
        latest_decision = None
        latest_intelligence = None
        latest_explanation = None
        latest_news_explanation = None
        latest_news = self._get_latest_news(selected_symbol)
        latest_snapshot = None

        for symbol in watchlist:
            stored_snapshot = self.snapshot_repository.get_latest_valid(symbol)
            if stored_snapshot is None:
                # Keep the explicitly selected market visible while ATLAS is
                # waiting for its first canonical runtime snapshot. This is
                # display-only market data; it must not create a decision.
                if symbol == selected_symbol:
                    try:
                        live_market = self.market_data.get(symbol)
                        price_usd = round(float(live_market.price), 2)
                        market.append({
                            "symbol": symbol,
                            "is_selected": True,
                            "favorite": False,
                            "price_usd": price_usd,
                            "price_nok": round(price_usd * exchange.rate, 2),
                            "change": round(float(live_market.change_percent), 2),
                            "trend": None,
                            "decision": "WAITING",
                            "confidence": None,
                            "evidence": None,
                        })
                    except Exception:
                        pass
                continue
            results = self._snapshot_results(stored_snapshot)
            decision = self._snapshot_decision(stored_snapshot)
            snapshot_intelligence = self._snapshot_intelligence(stored_snapshot)
            price_usd = stored_snapshot.decision.get("price_usd")
            live_market = None
            if price_usd is None:
                try:
                    live_market = self.market_data.get(symbol)
                    price_usd = live_market.price
                except Exception:
                    continue
            price_usd = round(float(price_usd), 2)
            change = round(float(live_market.change_percent), 2) if live_market is not None else None
            market.append({
                "symbol": symbol,
                "is_selected": symbol == selected_symbol,
                "favorite": False,
                "price_usd": price_usd,
                "price_nok": round(price_usd * exchange.rate, 2),
                "change": change,
                "trend": None,
                "decision": decision.action.value,
                "confidence": round(decision.confidence, 1),
                "evidence": round(decision.evidence, 1),
            })
            if symbol == selected_symbol:
                latest_results = results
                latest_decision = decision
                latest_intelligence = snapshot_intelligence
                latest_explanation = explain_decision(decision, agreement=snapshot_intelligence.agreement)
                latest_snapshot = stored_snapshot

        trading_status = self.settings.get_trading_status()
        if latest_decision is None or latest_intelligence is None or latest_snapshot is None:
            return {
                "status": "Waiting for ATLAS runtime",
                "version": "0.8.1",
                "capital": self.config.capital_limit,
                "trading": {
                    "mode": trading_status["mode"],
                    "language": self.settings.get_language(),
                    "ai_provider": self.settings.get_ai_provider(),
                    "paper_trading": trading_status["paper_trading"],
                    "live_orders": trading_status["live_orders"],
                    "virtual_capital_nok": self.config.capital_limit,
                },
                "portfolio": self.portfolio.as_dict(exchange.rate),
                "trade_history": [],
                "agent_performance": {
                    "history": self.agent_performance.history(),
                    "weights": self.agent_weight_engine.calculate(),
                    "weight_explanations": self.agent_weight_engine.explain(),
                },
                "currency": {"base": exchange.base, "target": exchange.target, "rate": round(exchange.rate, 4)},
                "decision": None,
                "decision_explanation": None,
                "news_explanation": None,
                "decision_robustness": {"margin": 0.0, "robustness": 0.0, "level": "WAITING"},
                "decision_influence": {"dominant_action": None, "dominant_weight": 0.0, "action_support_analyst": None, "action_support_action": None, "action_support_weight": 0.0, "opposing_analysts": [], "adaptive_override": False},
                "intelligence": None,
                "analysts": [],
                "market": market,
                "market_scan": self.market_scan(),
                "news": latest_news,
                "technical": None,
            }

        return {
            "status": "Running",
            "version": "0.8.1",
            "capital": self.config.capital_limit,
            "trading": {"mode": trading_status["mode"], "language": self.settings.get_language(), "ai_provider": self.settings.get_ai_provider(), "paper_trading": trading_status["paper_trading"], "live_orders": trading_status["live_orders"], "virtual_capital_nok": self.config.capital_limit},
            "portfolio": self.portfolio.as_dict(exchange.rate),
            "trade_history": self.trading.history(),
            "agent_performance": {"history": self.agent_performance.history(), "weights": self.agent_weight_engine.calculate(), "weight_explanations": self.agent_weight_engine.explain()},
            "currency": {"base": exchange.base, "target": exchange.target, "rate": round(exchange.rate, 4)},
            "decision": latest_decision,
            "decision_explanation": latest_explanation,
            "news_explanation": latest_news_explanation,
            "decision_robustness": {"margin": round(latest_decision.decision_margin, 1), "robustness": round(latest_decision.robustness, 1), "level": latest_decision.robustness_level},
            "decision_influence": {"dominant_action": latest_decision.dominant_action.value if latest_decision.dominant_action else None, "dominant_weight": round(latest_decision.dominant_weight, 1), "action_support_analyst": latest_decision.action_support_analyst, "action_support_action": latest_decision.action_support_action.value if latest_decision.action_support_action else None, "action_support_weight": round(latest_decision.action_support_weight * 100, 1), "opposing_analysts": latest_decision.opposing_analysts, "adaptive_override": latest_decision.adaptive_override},
            "intelligence": {"symbol": latest_intelligence.symbol, "action": latest_intelligence.action.value, "evidence": round(latest_intelligence.evidence, 1), "confidence": round(latest_intelligence.confidence, 1), "buy_count": latest_intelligence.buy_count, "hold_count": latest_intelligence.hold_count, "sell_count": latest_intelligence.sell_count, "agreement": round(latest_intelligence.agreement, 1), "conflict": latest_intelligence.conflict, "weighted_buy": round(latest_intelligence.weighted_buy, 1), "weighted_hold": round(latest_intelligence.weighted_hold, 1), "weighted_sell": round(latest_intelligence.weighted_sell, 1), "weighted_agreement": round(latest_intelligence.weighted_agreement, 1), "weighted_conflict": latest_intelligence.weighted_conflict, "analysts": latest_intelligence.analysts, "reasoning": latest_intelligence.reasoning},
            "analysts": latest_results,
            "market": market,
            "market_scan": self.market_scan(),
            "news": latest_news,
            "technical": None,
        }
