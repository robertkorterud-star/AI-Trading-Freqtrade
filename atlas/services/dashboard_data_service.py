"""
Dashboard Data Service

Collects all data required by the dashboard.
"""

from atlas.config.settings import settings
from atlas.core.config import AtlasConfig
from atlas.core.registry import AgentRegistry
from atlas.core.analysis_service import AnalysisService

from atlas.agents.news_analyst import NewsAnalyst
from atlas.agents.technical_analyst import TechnicalAnalyst
from atlas.agents.company_analyst import CompanyAnalyst

from atlas.decision.engine import DecisionEngine
from atlas.decision.intelligence_layer import IntelligenceLayer
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

        self.agent_performance = AgentPerformanceTracker(
            storage_path=self.config.agent_performance_storage
        )

        self.agent_weight_engine = AgentWeightEngine(
            self.agent_performance
        )

        self.decision.agent_weight_engine = (
            self.agent_weight_engine
        )

        for agent in self.registry.get_all():
            self.agent_performance.ensure(agent.name)

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
        latest_news = []
        latest_snapshot = None

        for symbol in watchlist:

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

            snapshot = self.technical.get_snapshot(
                symbol
            )

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
