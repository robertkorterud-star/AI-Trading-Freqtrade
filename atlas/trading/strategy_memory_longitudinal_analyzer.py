"""
ATLAS Strategy Memory Longitudinal Analyzer.

Analyzes strategy-memory history across multiple research runs.

Research-only.
This module does not generate trading decisions.
"""

from dataclasses import dataclass
from statistics import pstdev

from atlas.trading.strategy_memory import StrategyMemoryRecord


@dataclass(frozen=True, slots=True)
class StrategyMemoryLongitudinalAnalysis:
    observation_count: int
    average_return_percent: float
    best_return_percent: float
    worst_return_percent: float
    average_win_rate_percent: float
    average_trade_count: float
    positive_periods: int
    positive_period_ratio: float
    robust_winner_periods: int
    consistency_score: float
    confidence: float
    classification: str


class StrategyMemoryLongitudinalAnalyzer:
    """
    Analyze long-term strategy performance across research runs.

    Classification:

    - INSUFFICIENT_DATA: fewer than 2 observations
    - UNSTABLE: large performance variation
    - MIXED: meaningful positive/negative variation
    - CONSISTENT: predominantly positive and stable
    """

    MIN_OBSERVATIONS = 2

    CONSISTENT_POSITIVE_RATIO = 0.80
    CONSISTENT_MAX_VARIATION = 0.50
    UNSTABLE_MAX_VARIATION = 1.00

    def analyze(
        self,
        history: tuple[StrategyMemoryRecord, ...],
    ) -> StrategyMemoryLongitudinalAnalysis:

        if not history:
            return self._insufficient()

        returns = [
            float(record.total_return_percent)
            for record in history
        ]

        win_rates = [
            float(record.win_rate_percent)
            for record in history
        ]

        trade_counts = [
            float(record.trade_count)
            for record in history
        ]

        observation_count = len(history)

        average_return = (
            sum(returns) / observation_count
        )

        best_return = max(returns)
        worst_return = min(returns)

        average_win_rate = (
            sum(win_rates) / observation_count
        )

        average_trade_count = (
            sum(trade_counts) / observation_count
        )

        positive_periods = sum(
            1
            for value in returns
            if value > 0.0
        )

        positive_ratio = (
            positive_periods / observation_count
        )

        robust_winner_periods = sum(
            1
            for record in history
            if record.robust_winner
        )

        consistency_score = self._consistency_score(
            returns=returns,
            positive_ratio=positive_ratio,
        )

        classification = self._classification(
            returns=returns,
            positive_ratio=positive_ratio,
        )

        confidence = self._confidence(
            observation_count=observation_count,
            positive_ratio=positive_ratio,
            consistency_score=consistency_score,
        )

        return StrategyMemoryLongitudinalAnalysis(
            observation_count=observation_count,
            average_return_percent=round(
                average_return,
                4,
            ),
            best_return_percent=round(
                best_return,
                4,
            ),
            worst_return_percent=round(
                worst_return,
                4,
            ),
            average_win_rate_percent=round(
                average_win_rate,
                4,
            ),
            average_trade_count=round(
                average_trade_count,
                4,
            ),
            positive_periods=positive_periods,
            positive_period_ratio=positive_ratio,
            robust_winner_periods=robust_winner_periods,
            consistency_score=consistency_score,
            confidence=confidence,
            classification=classification,
        )

    @classmethod
    def _consistency_score(
        cls,
        *,
        returns: list[float],
        positive_ratio: float,
    ) -> float:

        if len(returns) < cls.MIN_OBSERVATIONS:
            return 0.0

        mean_abs = (
            sum(abs(value) for value in returns)
            / len(returns)
        )

        variation = (
            pstdev(returns) / mean_abs
            if mean_abs > 0.0
            else 1.0
        )

        stability_score = max(
            0.0,
            1.0 - min(variation, 1.0),
        )

        score = (
            positive_ratio * 70.0
            + stability_score * 30.0
        )

        return round(
            max(
                0.0,
                min(100.0, score),
            ),
            2,
        )

    @classmethod
    def _classification(
        cls,
        *,
        returns: list[float],
        positive_ratio: float,
    ) -> str:

        if len(returns) < cls.MIN_OBSERVATIONS:
            return "INSUFFICIENT_DATA"

        mean_abs = (
            sum(abs(value) for value in returns)
            / len(returns)
        )

        variation = (
            pstdev(returns) / mean_abs
            if mean_abs > 0.0
            else 1.0
        )

        performance_range = (
            max(returns) - min(returns)
        )

        if (
            variation >= cls.UNSTABLE_MAX_VARIATION
            or (
                min(returns) < 0.0
                and performance_range >= 75.0
            )
        ):
            return "UNSTABLE"

        if (
            positive_ratio
            >= cls.CONSISTENT_POSITIVE_RATIO
            and variation
            <= cls.CONSISTENT_MAX_VARIATION
        ):
            return "CONSISTENT"

        return "MIXED"

    @staticmethod
    def _confidence(
        *,
        observation_count: int,
        positive_ratio: float,
        consistency_score: float,
    ) -> float:

        if observation_count < 2:
            return 0.0

        observation_factor = min(
            1.0,
            observation_count / 10.0,
        )

        confidence = (
            consistency_score
            * observation_factor
        )

        return round(
            max(
                0.0,
                min(100.0, confidence),
            ),
            2,
        )

    @staticmethod
    def _insufficient() -> StrategyMemoryLongitudinalAnalysis:
        return StrategyMemoryLongitudinalAnalysis(
            observation_count=0,
            average_return_percent=0.0,
            best_return_percent=0.0,
            worst_return_percent=0.0,
            average_win_rate_percent=0.0,
            average_trade_count=0.0,
            positive_periods=0,
            positive_period_ratio=0.0,
            robust_winner_periods=0,
            consistency_score=0.0,
            confidence=0.0,
            classification="INSUFFICIENT_DATA",
        )
