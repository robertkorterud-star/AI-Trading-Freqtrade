"""
Strategy Learning Agent

Turns external trading research into testable strategy hypotheses.

This agent does NOT place trades.
"""

from atlas.agents.base_agent import BaseAgent
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult
from atlas.trading.strategy_hypothesis import StrategyHypothesis


class StrategyLearningAgent(BaseAgent):
    """Creates testable trading strategy hypotheses."""

    def __init__(self) -> None:
        super().__init__("Strategy Learning Agent")

    def analyze(self, symbol: str) -> AnalysisResult:
        """
        Satisfy the BaseAgent contract.

        Strategy discovery itself is performed by learn().
        """
        return AnalysisResult(
            analyst=self.name,
            symbol=symbol,
            action=Action.HOLD,
            confidence=0.0,
            evidence=0.0,
            reasoning=[
                "Strategy Learning Agent generates hypotheses "
                "from external research."
            ],
        )

    def learn(
        self,
        symbol: str,
        research: list[dict],
    ) -> list[StrategyHypothesis]:
        """
        Extract strategy hypotheses from research.

        Only explicit strategy ideas are converted into hypotheses.
        """

        hypotheses = []
        seen = set()

        for item in research:

            text = " ".join(
                [
                    item.get("title", ""),
                    item.get("summary", ""),
                    item.get("transcript", ""),
                ]
            ).lower()

            source = item.get(
                "source",
                "Unknown",
            )

            if "rsi" in text and (
                "oversold" in text
                or "below 30" in text
                or "under 30" in text
                or "rsi strategy" in text
                or "rsi trading" in text
            ):
                hypothesis = StrategyHypothesis(
                    name="RSI Oversold Reversal",
                        symbol=symbol,
                        timeframe="15m",
                        entry_rule=(
                            "RSI crosses back above 30 after being below 30"
                            if (
                                "cross back above 30" in text
                                or "crosses back above 30" in text
                                or "crossed back above 30" in text
                            )
                            else "RSI < 30"
                        ),
                        exit_rule="RSI > 50",
                        stop_loss="2%",
                        take_profit=(
                            "RSI >= 60"
                            if (
                                "take profit" in text
                                and (
                                    "rsi reaches 60" in text
                                    or "rsi reach 60" in text
                                    or "rsi hits 60" in text
                                    or "rsi hit 60" in text
                                )
                            )
                            else "4%"
                        ),
                        source=source,
                        reasoning=[
                            "Research mentions RSI oversold conditions.",
                            "Hypothesis requires historical backtesting.",
                        ],
                    )

                key = (
                    hypothesis.name,
                    hypothesis.symbol,
                    hypothesis.timeframe,
                    hypothesis.entry_rule,
                    hypothesis.exit_rule,
                    hypothesis.stop_loss,
                    hypothesis.take_profit,
                )

                if key not in seen:
                    seen.add(key)
                    hypotheses.append(hypothesis)

            if (
                "moving average" in text
                or "ma crossover" in text
                or "golden cross" in text
            ):
                hypothesis = StrategyHypothesis(
                    name="Moving Average Crossover",
                        symbol=symbol,
                        timeframe="1h",
                        entry_rule="MA20 crosses above MA50",
                        exit_rule="MA20 crosses below MA50",
                        stop_loss="3%",
                        take_profit="6%",
                        source=source,
                        reasoning=[
                            "Research mentions moving-average momentum.",
                            "Hypothesis requires historical backtesting.",
                        ],
                    )

                key = (
                    hypothesis.name,
                    hypothesis.symbol,
                    hypothesis.timeframe,
                    hypothesis.entry_rule,
                    hypothesis.exit_rule,
                    hypothesis.stop_loss,
                    hypothesis.take_profit,
                )

                if key not in seen:
                    seen.add(key)
                    hypotheses.append(hypothesis)

        return hypotheses
