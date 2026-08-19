"""
News Analyst

Analyzes recent financial news using the AI adapter.
"""

from atlas.agents.base_agent import BaseAgent
from atlas.adapters.news import NewsAdapter
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult
from atlas.core.ai_provider_factory import AIProviderFactory


class NewsAnalyst(BaseAgent):
    """AI-powered financial news analyst."""

    def __init__(self, config=None) -> None:
        super().__init__("News Analyst", config=config)

        self.news = NewsAdapter()

    def analyze(self, symbol: str) -> AnalysisResult:
        """
        Fetch recent news and analyze it with AI.

        This is the standard BaseAgent interface used by
        AnalysisService and AgentRegistry.
        """

        try:
            articles = self.news.latest(symbol)

            return self.analyze_news(
                symbol,
                articles,
            )

        except Exception as error:
            return AnalysisResult(
                analyst=self.name,
                symbol=symbol,
                action=Action.HOLD,
                confidence=0.0,
                evidence=60.0,
                reasoning=[
                    "AI news analysis unavailable.",
                    f"Fallback reason: {type(error).__name__}.",
                ],
            )

    @staticmethod
    def _article_fields(article):
        """Extract common fields from NewsItem or dict."""

        if isinstance(article, dict):
            return (
                article.get("title", ""),
                article.get("summary", ""),
                article.get("source", ""),
            )

        return (
            getattr(article, "title", ""),
            getattr(article, "summary", ""),
            getattr(article, "source", ""),
        )

    def analyze_news(
        self,
        symbol: str,
        articles: list,
    ) -> AnalysisResult:
        """
        Analyze supplied news using the AI adapter.

        The AI produces the interpretation. This method converts
        that interpretation into the standardized ATLAS
        AnalysisResult format.
        """

        if not articles:
            return AnalysisResult(
                analyst=self.name,
                symbol=symbol,
                action=Action.HOLD,
                confidence=0.0,
                evidence=60.0,
                reasoning=[
                    "No relevant news available.",
                ],
            )

        ai = AIProviderFactory.create(
            config=self.config,
        )

        analysis = ai.analyze_news(
            symbol,
            articles,
        )

        action_name = str(
            analysis.get("action", "HOLD")
        ).upper()

        try:
            action = Action(action_name)
        except ValueError:
            action = Action.HOLD

        confidence = float(
            analysis.get("confidence", 0)
        )

        relevance = float(
            analysis.get("relevance", 0)
        )

        sentiment = str(
            analysis.get("sentiment", "NEUTRAL")
        ).upper()

        impact = str(
            analysis.get("impact", "LOW")
        ).upper()

        time_horizon = str(
            analysis.get("time_horizon", "SHORT")
        ).upper()

        reason = str(
            analysis.get(
                "reason",
                "AI news analysis completed.",
            )
        )

        # -------------------------------------------------
        # Convert AI's directional signal into ATLAS
        # evidence.
        #
        # Relevance is deliberately NOT used directly as
        # evidence. A highly relevant article can still
        # support HOLD or SELL.
        # -------------------------------------------------

        if action == Action.BUY:

            evidence = 80.0

            if impact == "HIGH":
                evidence += 10.0
            elif impact == "MEDIUM":
                evidence += 5.0

            if sentiment == "POSITIVE":
                evidence += 5.0

            evidence = min(
                evidence,
                100.0,
            )

        elif action == Action.SELL:

            evidence = 40.0

            if impact == "HIGH":
                evidence -= 10.0
            elif impact == "MEDIUM":
                evidence -= 5.0

            if sentiment == "NEGATIVE":
                evidence -= 5.0

            evidence = max(
                evidence,
                0.0,
            )

        else:

            evidence = 70.0

            if impact == "LOW":
                evidence -= 5.0

            if sentiment == "MIXED":
                evidence += 5.0

            evidence = max(
                60.0,
                min(evidence, 79.0),
            )

        reasoning = [
            f"AI news sentiment: {sentiment}.",
            f"News relevance: {relevance:.0f}/100.",
            f"Market impact: {impact}.",
            f"Time horizon: {time_horizon}.",
            f"AI confidence: {confidence:.0f}/100.",
            reason,
            f"Analyzed {len(articles)} news article(s) for {symbol}.",
        ]

        return AnalysisResult(
            analyst=self.name,
            symbol=symbol,
            action=action,
            confidence=confidence,
            evidence=evidence,
            reasoning=reasoning,
        )

    def analyze_with_news(
        self,
        symbol: str,
        articles: list,
    ) -> AnalysisResult:
        """
        Analyze already-fetched news.

        Useful for tests and for callers that already have
        a news collection.
        """

        try:
            return self.analyze_news(
                symbol,
                articles,
            )

        except Exception as error:
            return AnalysisResult(
                analyst=self.name,
                symbol=symbol,
                action=Action.HOLD,
                confidence=0.0,
                evidence=60.0,
                reasoning=[
                    "AI news analysis unavailable.",
                    f"Fallback reason: {type(error).__name__}.",
                ],
            )
