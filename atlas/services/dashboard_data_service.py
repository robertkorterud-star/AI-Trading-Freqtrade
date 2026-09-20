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
from atlas.services.trade_history_service import TradeHistoryService
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

    def __init__(self, config=None, intelligence_sources=None, trading=None):
        self.config = config or AtlasConfig()
        self.settings = SettingsService(config=self.config)
        self.registry = AgentRegistry()
        self.registry.register(NewsAnalyst(config=self.config))
        self.registry.register(TechnicalAnalyst())
        self.registry.register(CompanyAnalyst())
        self.exchange = ExchangeRateService()
        self.portfolio = PortfolioService()
        self.trading = trading or TradingService()
        self.trade_history = TradeHistoryService()
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
        snapshots = {
            asset.symbol: self.snapshot_repository.get_latest_valid(asset.symbol)
            for asset in self.asset_universe.all()
        }
        available_assets = [
            asset
            for asset in self.asset_universe.all()
            if snapshots[asset.symbol] is not None
        ]
        if not available_assets:
            return []

        try:
            discovered = self.asset_discovery.discover(
                AssetUniverse(assets=available_assets),
                limit=limit,
            )
        except Exception:
            discovered = []
        candidates = []
        for item in discovered:
            snapshot = snapshots.get(item.symbol)
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
            result = self.intelligence_sources.get(symbol, include_transcripts=False)
        except Exception:
            result = []

        if not isinstance(result, list):
            result = []

        # Keep the complete current-news feed, but make its leading items useful
        # to the overview. IntelligenceSourceAdapter groups results by adapter,
        # so without this pass a large YouTube result set hides every other
        # available source behind the template's first-five limit.
        by_source = {}
        source_order = []
        for item in result:
            source = item.get("source", "") if isinstance(item, dict) else ""
            source = str(source).strip() or "Unknown"
            if source not in by_source:
                by_source[source] = []
                source_order.append(source)
            by_source[source].append(item)

        diversified = []
        for source in source_order:
            diversified.append(by_source[source].pop(0))
        for source in source_order:
            diversified.extend(by_source[source])

        result = diversified
        self._news_cache[symbol] = (now, result)
        return result

    def _dashboard_trade_history(self, period, now=None):
        """Build dashboard trade history and attach its canonical snapshot context."""
        result = self.trade_history.build(
            self.trading.history(),
            period=period,
            now=now,
        )
        trades = []
        for trade in result["trades"]:
            data = trade.as_dict()
            snapshot_id = data.get("analysis_snapshot_id")
            snapshot = None
            if snapshot_id is not None:
                snapshot = self.snapshot_repository.get_by_id(int(snapshot_id))
            data["analysis_snapshot"] = (
                snapshot.as_dict()
                if snapshot is not None
                else None
            )
            trades.append(data)
        return {
            "trades": trades,
            "markers": result["markers"],
        }

    def get_dashboard_data(self, selected_symbol=None, trade_history_period="1d", now=None):
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
        history = self._dashboard_trade_history(trade_history_period, now=now)
        snapshots = {
            symbol: self.snapshot_repository.get_latest_valid(symbol)
            for symbol in watchlist
        }
        live_symbols = [
            symbol
            for symbol in watchlist
            if snapshots[symbol] is None
            or snapshots[symbol].decision.get("price_usd") is None
        ]
        live_market_data = self.market_data.get_many(live_symbols)
        trade_chart = {
            "period": trade_history_period,
            "symbol": selected_symbol,
            "trades": history["trades"],
            "markers": [
                marker
                for marker in history["markers"]
                if marker["symbol"] == selected_symbol
            ],
        }

        for symbol in watchlist:
            stored_snapshot = snapshots[symbol]
            live_market = live_market_data.get(symbol)
            if stored_snapshot is None:
                if symbol == selected_symbol:
                    try:
                        if live_market is None:
                            raise ValueError("No live market data available.")
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
            if price_usd is None:
                if live_market is None:
                    continue
                price_usd = live_market.price
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
        trading_data = {
            "mode": trading_status["mode"],
            "language": self.settings.get_language(),
            "ai_provider": self.settings.get_ai_provider(),
            "paper_trading": trading_status["paper_trading"],
            "live_orders": trading_status["live_orders"],
            "accumulation_drop_pct": trading_status["accumulation_drop_pct"],
            "virtual_capital_nok": self.config.capital_limit,
        }
        if latest_decision is None or latest_intelligence is None or latest_snapshot is None:
            return {
                "status": "Waiting for ATLAS runtime",
                "version": "0.8.1",
                "capital": self.config.capital_limit,
                "trading": trading_data,
                "portfolio": self.portfolio.as_dict(exchange.rate),
                "trade_history": history["trades"],
                "trade_history_markers": history["markers"],
                "trade_history_period": trade_history_period,
                "trade_chart": trade_chart,
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
            "trading": trading_data,
            "portfolio": self.portfolio.as_dict(exchange.rate),
            "trade_history": history["trades"],
            "trade_history_markers": history["markers"],
            "trade_history_period": trade_history_period,
            "trade_chart": trade_chart,
            "agent_performance": {"history": self.agent_performance.history(), "weights": self.agent_weight_engine.calculate(), "weight_explanations": self.agent_weight_engine.explain()},
            "currency": {"base": exchange.base, "target": exchange.target, "rate": round(exchange.rate, 4)},
            "decision": latest_decision,
            "decision_explanation": latest_explanation,
            "news_explanation": latest_news_explanation,
            "decision_robustness": {"margin": latest_decision.decision_margin, "robustness": latest_decision.robustness, "level": latest_decision.robustness_level},
            "decision_influence": {"dominant_action": latest_decision.dominant_action.value if latest_decision.dominant_action else None, "dominant_weight": latest_decision.dominant_weight, "action_support_analyst": latest_decision.action_support_analyst, "action_support_action": latest_decision.action_support_action.value if latest_decision.action_support_action else None, "action_support_weight": latest_decision.action_support_weight, "opposing_analysts": latest_decision.opposing_analysts, "adaptive_override": latest_decision.adaptive_override},
            "intelligence": latest_intelligence,
            "analysts": latest_results,
            "market": market,
            "market_scan": self.market_scan(),
            "news": latest_news,
            "technical": next((result for result in latest_results if result.analyst == "Technical Analyst"), None),
        }
