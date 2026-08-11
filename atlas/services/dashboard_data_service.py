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

from atlas.decision.engine import DecisionEngine
from atlas.adapters.news import NewsAdapter

from atlas.services.technical_service import TechnicalService
from atlas.services.exchange_rate_service import ExchangeRateService
from atlas.services.portfolio_service import PortfolioService
from atlas.trading.trading_service import TradingService


class DashboardDataService:
    """Collects dashboard data."""

    def __init__(self):

        self.config = AtlasConfig()

        self.registry = AgentRegistry()

        self.registry.register(NewsAnalyst())
        self.registry.register(TechnicalAnalyst())

        self.analysis = AnalysisService(self.registry)
        self.decision = DecisionEngine()
        self.news = NewsAdapter()
        self.technical = TechnicalService()
        self.exchange = ExchangeRateService()
        self.portfolio = PortfolioService()
        self.trading = TradingService()

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
        latest_news = []
        latest_snapshot = None

        for symbol in watchlist:

            results = self.analysis.analyze(symbol)

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

        return {

            "status": "Running",

            "version": "0.8.1",

            "capital": self.config.capital_limit,

            "trading": {

                "mode": self.config.trading_mode,

                "paper_trading": (
                    self.config.paper_trading
                ),

                "live_orders": False,

                "virtual_capital_nok": (
                    self.config.capital_limit
                ),

            },

            "portfolio": (
                self.portfolio.as_dict(
                    exchange.rate
                )
            ),

            "trade_history": self.trading.history(),

            "currency": {

                "base": exchange.base,

                "target": exchange.target,

                "rate": round(
                    exchange.rate,
                    4,
                ),

            },

            "decision": latest_decision,

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
