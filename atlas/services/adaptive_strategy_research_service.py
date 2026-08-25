from atlas.services.strategy_research_service import (
    StrategyResearchResult,
    StrategyResearchService,
)


class AdaptiveStrategyResearchService:
    """Run one controlled feedback-driven research round."""

    def __init__(
        self,
        strategy_research=None,
        web_research=None,
    ) -> None:

        self.strategy_research = (
            strategy_research
            if strategy_research is not None
            else StrategyResearchService()
        )

        self.web_research = web_research

    def research(
        self,
        symbol: str,
        research: list[dict],
    ) -> StrategyResearchResult:

        initial = self.strategy_research.research(
            symbol,
            research,
        )

        if not initial.assessments:
            initial.history = [initial]
            return initial

        adaptive_items = []

        for assessment in initial.assessments:

            if assessment.status != "REJECT":
                continue

            if self.web_research is None:
                continue

            adaptive_items.extend(
                self.web_research.search(
                    symbol,
                    focus=assessment.next_focus,
                )
            )

        if not adaptive_items:
            initial.history = [initial]
            return initial

        final = self.strategy_research.research(
            symbol,
            adaptive_items,
        )

        final.history = [
            initial,
            final,
        ]

        return final
