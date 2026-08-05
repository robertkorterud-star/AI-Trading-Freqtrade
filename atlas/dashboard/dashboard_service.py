"""
Dashboard Service
"""

from atlas.core.registry import AgentRegistry
from atlas.core.analysis_service import AnalysisService

from atlas.agents.news_analyst import NewsAnalyst
from atlas.agents.technical_analyst import TechnicalAnalyst
from atlas.decision.engine import DecisionEngine


class DashboardService:
    """Provides data for the dashboard."""

    def __init__(self):

        self.registry = AgentRegistry()

        self.registry.register(NewsAnalyst())

        self.registry.register(TechnicalAnalyst())

        self.analysis = AnalysisService(self.registry)

        self.decision = DecisionEngine()

    def get_dashboard(self):

        results = self.analysis.analyze("BTC")

        decision = self.decision.evaluate(results)

        return {

            "status": "Running",

            "version": "0.4 Alpha",

            "capital": 5000,

            "decision": decision,

            "analysts": results,

        }