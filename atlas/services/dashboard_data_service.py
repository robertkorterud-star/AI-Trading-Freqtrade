"""
Dashboard Data Service

Collects all data required by the dashboard.
"""

from atlas.config.settings import settings
from atlas.core.config import AtlasConfig
from atlas.core.registry import AgentRegistry
from atlas.core.analysis_service import AnalysisService

from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult
from atlas.models.decision_result import DecisionResult
from atlas.models.intelligence_summary import IntelligenceSummary

from atlas.agents.news_analyst import NewsAnalyst
from atlas.agents.technical_analyst import TechnicalAnalyst
from atlas.agents.company_analyst import CompanyAnalyst

from atlas.decision.engine import DecisionEngine
from atlas.decision.intelligence_layer import IntelligenceLayer
from atlas.decision.explanation import explain_decision
from atlas.adapters.news import NewsAdapter

from atlas.services.technical_service import TechnicalService
from atlas.services.exchange_rate_service import ExchangeRateService
from atlas.services.portfolio_service import PortfolioService
from atlas.trading.trading_service import TradingService
from atlas.services.settings_service import SettingsService
from atlas.trading.agent_performance_tracker import (
    AgentPerformanceTracker,
)
from atlas.trading.agent_weight_engine import AgentWeightEngine

from atlas.database.connection import Database
from atlas.database.analysis_snapshot_repository import (
    AnalysisSnapshotRepository,
)
from atlas.database.prediction_repository import (
    PredictionRepository,
)

from atlas.market.asset_universe import AssetUniverse
from atlas.market.asset_discovery import AssetDiscoveryService
from atlas.adapters.market_data import MarketDataAdapter
from atlas.market.candidate_decision_ranker import (
    CandidateDecisionRanker,
)


class DashboardDataService:
    """Collects dashboard data."""

    def __init__(self, config=None):

        self.config = config or AtlasConfig()

        self.settings = SettingsService(
            config=self.config,
        )

        self.registry = AgentRegistry()

        self.registry.register(
            NewsAnalyst(
                config=self.config,
            )
        )
        self.registry.register(TechnicalAnalyst())
        self.registry.register(CompanyAnalyst())

        self.analysis = AnalysisService(self.registry)
        self.decision = DecisionEngine()
        self.intelligence = IntelligenceLayer()
        self.news = NewsAdapter()
        self.technical = TechnicalService()
        self.exchange = ExchangeRateService()
        self.portfolio = PortfolioService()
        self.trading = TradingService()

        self.asset_universe = AssetUniverse()
        self.market_data = MarketDataAdapter()
        self.asset_discovery = AssetDiscoveryService(
            market_data=self.market_data,
        )
        self.candidate_decision_ranker = (
            CandidateDecisionRanker()
        )

        database = Database(
            self.config.database_path
        )

        self.snapshot_repository = (
            AnalysisSnapshotRepository(
                database
            )
        )

        self.prediction_repository = (
            PredictionRepository(
                database
            )
        )

        self.agent_performance = AgentPerformanceTracker(
            storage_path=self.config.agent_performance_storage
        )

        has_performance_history = any(
            item["predictions"] > 0
            for item in self.agent_performance.history()
        )

        if not has_performance_history:
            evaluated_predictions = (
                self.prediction_repository.get_evaluated()
            )

            if evaluated_predictions:
                self.agent_performance.rebuild_from_predictions(
                    evaluated_predictions
                )

        self.agent_weight_engine = AgentWeightEngine(
            self.agent_performance
        )

        self.decision.agent_weight_engine = (
            self.agent_weight_engine
        )

        for agent in self.registry.get_all():
            self.agent_performance.ensure(agent.name)

    @staticmethod
    def _snapshot_results(snapshot):
        """Rebuild AnalysisResult objects from a snapshot."""

        return [
            AnalysisResult(
                analyst=result["analyst"],
                symbol=result["symbol"],
                action=Action(result["action"]),
                confidence=float(result["confidence"]),
                evidence=float(result["evidence"]),
                reasoning=list(
                    result.get("reasoning", [])
                ),
            )
            for result in snapshot.results
        ]

    @staticmethod
    def _snapshot_decision(snapshot):
        """Rebuild DecisionResult from a snapshot."""

        data = snapshot.decision

        dominant_action = data.get(
            "dominant_action"
        )

        return DecisionResult(
            symbol=data["symbol"],
            action=Action(data["action"]),
            confidence=float(data["confidence"]),
            evidence=float(data["evidence"]),
            analysts=list(
                data.get("analysts", [])
            ),
            agent_weights=dict(
                data.get("agent_weights", {})
            ),
            dominant_action=(
                Action(dominant_action)
                if dominant_action
                else None
            ),
            dominant_weight=float(
                data.get("dominant_weight", 0.0)
            ),
            opposing_analysts=list(
                data.get("opposing_analysts", [])
            ),
            adaptive_override=bool(
                data.get("adaptive_override", False)
            ),
            decision_margin=float(
                data.get("decision_margin", 0.0)
            ),
            robustness=float(
                data.get("robustness", 0.0)
            ),
            robustness_level=data.get(
                "robustness_level",
                "WEAK",
            ),
            reasoning=list(
                data.get("reasoning", [])
            ),
        )

    @staticmethod
    def _snapshot_intelligence(snapshot):
        """Rebuild IntelligenceSummary from a snapshot."""

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
            weighted_buy=float(
                data.get("weighted_buy", 0.0)
            ),
            weighted_hold=float(
                data.get("weighted_hold", 0.0)
            ),
            weighted_sell=float(
                data.get("weighted_sell", 0.0)
            ),
            weighted_agreement=float(
                data.get("weighted_agreement", 0.0)
            ),
            weighted_conflict=bool(
                data.get("weighted_conflict", False)
            ),
            analysts=list(
                data.get("analysts", [])
            ),
            reasoning=list(
                data.get("reasoning", [])
            ),
        )

    def market_scan(self, limit=5):
        'Return a lightweight ranked market scan for the dashboard.'

        try:
            discovered = self.asset_discovery.discover(
                self.asset_universe,
                limit=limit,
            )
        except Exception:
            discovered = []

        candidates = []

        for item in discovered:
            snapshot = (
                self.snapshot_repository.get_latest_valid(
                    item.symbol
                )
            )

            if snapshot is None:
                continue

            decision = self._snapshot_decision(
                snapshot
            )

            candidates.append(
                {
                    "symbol": item.symbol,
                    "discovery_score": round(
                        item.score,
                        1,
                    ),
                    "decision": decision,
                }
            )

        ranked = self.candidate_decision_ranker.rank(
            [
                item["decision"]
                for item in candidates
            ]
        )

        selected_symbol = (
            ranked[0].symbol
            if ranked
            else None
        )

        by_symbol = {
            item["symbol"]: item
            for item in candidates
        }

        result = []

        for decision in ranked:
            item = by_symbol[decision.symbol]

            result.append(
                {
                    "symbol": decision.symbol,
                    "discovery_score": item[
                        "discovery_score"
                    ],
                    "decision": decision.action.value,
                    "confidence": round(
                        decision.confidence,
                        1,
                    ),
                    "selected": (
                        decision.symbol
                        == selected_symbol
                    ),
                }
            )

        return result

    def get_dashboard_data(self, selected_symbol=None):

        watchlist = [
            "BTC-USD",
            "ETH-USD",
            "SOL-USD",
            "NVDA",
        ]

        selected_symbol = (
            selected_symbol
            or settings.default_symbol
        )

        if selected_symbol not in watchlist:
            selected_symbol = settings.default_symbol

        exchange = self.exchange.get_rate(
            "USD",
            "NOK",
        )

        market = []

        latest_results = None
        latest_decision = None
        latest_intelligence = None
        latest_explanation = None
        latest_news_explanation = None
        latest_news = []
        latest_snapshot = None


        for symbol in watchlist:

            stored_snapshot = (
                self.snapshot_repository.get_latest_valid(
                    symbol
                )
            )

            if stored_snapshot is not None:

                results = self._snapshot_results(
                    stored_snapshot
                )

                decision = self._snapshot_decision(
                    stored_snapshot
                )

                latest_snapshot_intelligence = (
                    self._snapshot_intelligence(
                        stored_snapshot
                    )
                )

            else:

                try:

                    if symbol == selected_symbol:

                        news = self.news.latest(symbol)

                        results = self.analysis.analyze_with_news(
                            symbol,
                            news,
                        )

                    else:

                        results = self.analysis.analyze(
                            symbol,
                            exclude={"News Analyst"},
                        )

                    decision = self.decision.evaluate(
                        results
                    )

                    latest_snapshot_intelligence = (
                        self.intelligence.summarize(
                            results,
                            weights=decision.agent_weights,
                        )
                    )

                except Exception:
                    if symbol == selected_symbol:
                        raise

                    continue

            try:
                snapshot = self.technical.get_snapshot(
                    symbol
                )
            except Exception:
                if symbol == selected_symbol:
                    raise

                continue

            price_usd = round(
                snapshot.price,
                2,
            )

            price_nok = round(
                snapshot.price * exchange.rate,
                2,
            )

            market.append(
                {
                    "symbol": symbol,

                    "is_selected": (
                        symbol == selected_symbol
                    ),

                    "favorite": False,

                    "price_usd": price_usd,

                    "price_nok": price_nok,

                    "change": round(
                        snapshot.change_percent,
                        2,
                    ),

                    "trend": snapshot.trend,

                    "decision": (
                        decision.action.value
                    ),

                    "confidence": round(
                        decision.confidence,
                        1,
                    ),

                    "evidence": round(
                        decision.evidence,
                        1,
                    ),
                }
            )

            if symbol == selected_symbol:

                latest_results = results

                latest_decision = decision

                latest_intelligence = (
                    self.intelligence.summarize(
                        results,
                        weights=decision.agent_weights,
                    )
                )

                latest_explanation = explain_decision(
                    decision,
                    agreement=latest_intelligence.agreement,
                )

                news_analyst = next(
                    (
                        agent
                        for agent in self.registry.get_all()
                        if agent.name == "News Analyst"
                    ),
                    None,
                )

                latest_news_explanation = (
                    getattr(
                        news_analyst,
                        "news_explanation",
                        None,
                    )
                )

                latest_snapshot = snapshot

                latest_news = self.news.latest(
                    symbol
                )

        # Update prices for any existing
        # paper-trading positions.
        prices_usd = {
        item["symbol"]: item["price_usd"]
        for item in market
        }

        self.portfolio.update_prices(
        prices_usd
        )

        portfolio_data = self.portfolio.as_dict(
        exchange.rate
        )

        return {

        "status": "Running",

        "version": "0.8.1",

        "capital": self.config.capital_limit,

        "trading": {

            "mode": self.settings.get_trading_status()["mode"],

            "language": self.settings.get_language(),

            "ai_provider": self.settings.get_ai_provider(),

            "paper_trading": (
                self.settings.get_trading_status()["paper_trading"]
            ),

            "live_orders": (
                self.settings.get_trading_status()["live_orders"]
            ),

            "virtual_capital_nok": (
                self.config.capital_limit
            ),

            "cash_nok": portfolio_data["cash_nok"],

            "invested_nok": portfolio_data["invested_nok"],

            "positions_value_nok": (
                portfolio_data["positions_value_nok"]
            ),

            "position_count": (
                portfolio_data["position_count"]
            ),

            "unrealized_pnl_nok": (
                portfolio_data["unrealized_pnl_nok"]
            ),

            "total_pnl_nok": (
                portfolio_data["total_pnl_nok"]
            ),

            "return_percent": (
                portfolio_data["return_percent"]
            ),

        },

        "portfolio": portfolio_data,

        "trade_history": self.trading.history(),

        "agent_performance": {
        "history": self.agent_performance.history(),
        "weights": self.agent_weight_engine.calculate(),
        "weight_explanations": (
            self.agent_weight_engine.explain()
        ),
        },

        "currency": {

            "base": exchange.base,

            "target": exchange.target,

            "rate": round(
                exchange.rate,
                4,
            ),

        },

        "decision": latest_decision,

        "decision_explanation": latest_explanation,

        "news_explanation": latest_news_explanation,

        "decision_robustness": {
            "margin": round(
                latest_decision.decision_margin,
                1,
            ),
            "robustness": round(
                latest_decision.robustness,
                1,
            ),
            "level": latest_decision.robustness_level,
        },

        "decision_influence": {
            "dominant_action": (
                latest_decision.dominant_action.value
                if latest_decision.dominant_action
                else None
            ),
            "dominant_weight": round(
                latest_decision.dominant_weight,
                1,
            ),
            "opposing_analysts": (
                latest_decision.opposing_analysts
            ),
            "adaptive_override": (
                latest_decision.adaptive_override
            ),
        },

        "intelligence": {
            "symbol": latest_intelligence.symbol,
            "action": latest_intelligence.action.value,
            "evidence": round(
                latest_intelligence.evidence,
                1,
            ),
            "confidence": round(
                latest_intelligence.confidence,
                1,
            ),
            "buy_count": latest_intelligence.buy_count,
            "hold_count": latest_intelligence.hold_count,
            "sell_count": latest_intelligence.sell_count,
            "agreement": round(
                latest_intelligence.agreement,
                1,
            ),
            "conflict": latest_intelligence.conflict,
            "weighted_buy": round(
                latest_intelligence.weighted_buy,
                1,
            ),
            "weighted_hold": round(
                latest_intelligence.weighted_hold,
                1,
            ),
            "weighted_sell": round(
                latest_intelligence.weighted_sell,
                1,
            ),
            "weighted_agreement": round(
                latest_intelligence.weighted_agreement,
                1,
            ),
            "weighted_conflict": (
                latest_intelligence.weighted_conflict
            ),
            "analysts": latest_intelligence.analysts,
            "reasoning": latest_intelligence.reasoning,
        },

        "analysts": latest_results,

        "market": market,

        "market_scan": self.market_scan(),

        "news": latest_news,

        "technical": {

            "symbol": latest_snapshot.symbol,

            "price_usd": round(
                latest_snapshot.price,
                2,
            ),

            "price_nok": round(
                latest_snapshot.price
                * exchange.rate,
                2,
            ),

            "change": round(
                latest_snapshot.change_percent,
                2,
            ),

            "ma20": round(
                latest_snapshot.ma20,
                2,
            ),

            "ma50": round(
                latest_snapshot.ma50,
                2,
            ),

            "trend": latest_snapshot.trend,

        },

        }
