from atlas.services.strategy_research_service import (
    StrategyResearchResult,
    StrategyResearchService,
)


class AdaptiveStrategyResearchService:
    """Run a bounded feedback-driven research process."""

    MAX_ROUNDS = 3

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
        """Run up to MAX_ROUNDS, stopping early on PASS."""

        current = self.strategy_research.research(
            symbol,
            research,
        )

        history = [current]

        for _ in range(
            self.MAX_ROUNDS - 1
        ):

            if not current.assessments:
                break

            if any(
                assessment.status == "PASS"
                for assessment in current.assessments
            ):
                break

            rejected = [
                assessment
                for assessment in current.assessments
                if assessment.status == "REJECT"
            ]

            if not rejected:
                break

            if self.web_research is None:
                break

            focus = []

            for assessment in rejected:
                for term in assessment.next_focus:
                    if term not in focus:
                        focus.append(term)

            if not focus:
                break

            adaptive_items = self.web_research.search(
                symbol,
                focus=tuple(focus),
            )

            if not adaptive_items:
                break

            next_result = self.strategy_research.research(
                symbol,
                adaptive_items,
            )

            if not next_result.strategies:
                break

            current = next_result
            history.append(current)

        current.history = history

        return current
