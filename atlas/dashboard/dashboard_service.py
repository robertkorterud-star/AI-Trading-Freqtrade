"""
Dashboard Service
"""

from atlas.core.registry import AgentRegistry
from atlas.core.analysis_service import AnalysisService

from atlas.agents.news_analyst import NewsAnalyst
from atlas.agents.technical_analyst import TechnicalAnalyst

from atlas.decision.engine import DecisionEngine

from atlas.adapters.news import NewsAdapter
from atlas.services.technical_service import TechnicalService


class DashboardService:
    """Provides data for the dashboard."""

    def __init__(self):

        self.registry = AgentRegistry()

        self.registry.register(NewsAnalyst())
        self.registry.register(TechnicalAnalyst())

        self.analysis = AnalysisService(self.registry)
        self.decision = DecisionEngine()

        self.news = NewsAdapter()
        self.technical = TechnicalService()

    def get_dashboard(self):

        watchlist = [
            "BTC-USD",
            "ETH-USD",
            "SOL-USD",
            "NVDA",
        ]

        market = []

        latest_results = None
        latest_decision = None
        latest_news = []
        latest_snapshot = None

        for symbol in watchlist:

            # AI Analysis
            results = self.analysis.analyze(symbol)

            decision = self.decision.evaluate(results)

            # Technical Analysis
            snapshot = self.technical.get_snapshot(symbol)

            market.append(
                {
                    "symbol": symbol,
                    "price": round(snapshot.price, 2),
                    "change": round(snapshot.change_percent, 2),
                    "trend": snapshot.trend,
                    "decision": decision.action.value,
                    "confidence": decision.confidence,
                    "evidence": decision.evidence,
                }
            )

            if symbol == "BTC-USD":

                latest_results = results
                latest_decision = decision
                latest_snapshot = snapshot
                latest_news = self.news.latest(symbol)

        return {

            "status": "Running",

            "version": "0.5 Beta",

            "capital": 5000,

            "decision": latest_decision,

            "analysts": latest_results,

            "market": market,

            "news": latest_news,

            "technical": {

                "symbol": latest_snapshot.symbol,

                "price": round(latest_snapshot.price, 2),

                "change": round(latest_snapshot.change_percent, 2),

                "ma20": round(latest_snapshot.ma20, 2),

                "ma50": round(latest_snapshot.ma50, 2),

                "trend": latest_snapshot.trend,

            }

        }