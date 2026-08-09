"""
Dashboard Service
"""

from atlas.core.registry import AgentRegistry
from atlas.core.analysis_service import AnalysisService

from atlas.agents.news_analyst import NewsAnalyst
from atlas.agents.technical_analyst import TechnicalAnalyst

from atlas.decision.engine import DecisionEngine
from atlas.services.technical_service import TechnicalService

from atlas.adapters.news import NewsAdapter


class DashboardService:
    """Provides data for the dashboard."""

    def __init__(self):

        self.registry = AgentRegistry()

        self.registry.register(NewsAnalyst())
        self.registry.register(TechnicalAnalyst())

        self.analysis = AnalysisService(self.registry)
        self.decision = DecisionEngine()

        self.technical = TechnicalService()
        self.news = NewsAdapter()

    def get_dashboard(self, symbol: str = "BTC-USD"):

        # Run AI analysts
        results = self.analysis.analyze(symbol)

        # AI decision
        decision = self.decision.evaluate(results)

        # Technical data
        snapshot = self.technical.get_snapshot(symbol)

        # News
        try:
            news = self.news.get_news(symbol)
        except Exception:
            news = []

        return {
            "status": "Running",
            "version": "0.5 Beta",
            "capital": 5000,

            "decision": decision,
            "analysts": results,

            "symbol": snapshot.symbol,
            "price": round(snapshot.price, 2),
            "change": round(snapshot.change_percent, 2),
            "ma20": round(snapshot.ma20, 2),
            "ma50": round(snapshot.ma50, 2),
            "trend": snapshot.trend,

            "news": news,
        }