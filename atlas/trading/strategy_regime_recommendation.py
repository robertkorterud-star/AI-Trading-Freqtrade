"""
ATLAS Strategy Regime Recommendation.

Research-only recommendation of which strategy has
historically performed best within a market regime.

This module does not generate BUY/SELL decisions.
"""

from dataclasses import dataclass

from atlas.trading.regime_strategy_backtest import (
    RegimeStrategyBacktestSummary,
)


@dataclass(frozen=True, slots=True)
class StrategyRegimeRecommendation:
    regime: str
    recommended_strategy: str | None
    confidence: float
    trade_count: int
    average_trade_return_percent: float
    total_return_percent: float
    reason: str


class StrategyRegimeRecommender:
    """
    Recommend the historically strongest strategy for a regime.

    Confidence is based on:
    - amount of historical evidence
    - average trade return
    - consistency of the result
    """

    def recommend(
        self,
        summary: RegimeStrategyBacktestSummary,
        regime: str,
    ) -> StrategyRegimeRecommendation:

        candidates = [
            result
            for result in summary.results
            if result.regime == regime
            and result.trade_count > 0
        ]

        if not candidates:
            return StrategyRegimeRecommendation(
                regime=regime,
                recommended_strategy=None,
                confidence=0.0,
                trade_count=0,
                average_trade_return_percent=0.0,
                total_return_percent=0.0,
                reason=(
                    "No historical strategy trades "
                    "were recorded for this regime."
                ),
            )

        winner = max(
            candidates,
            key=lambda result: (
                result.total_return_percent,
                result.average_trade_return_percent,
                result.trade_count,
                -result.losing_trades,
                result.strategy_name,
            ),
        )

        confidence = self._confidence(
            trade_count=winner.trade_count,
            average_return=(
                winner.average_trade_return_percent
            ),
        )

        reason = (
            f"{winner.strategy_name} had the strongest "
            f"historical result in {regime}, with "
            f"{winner.trade_count} trades and an average "
            f"trade return of "
            f"{winner.average_trade_return_percent:.3f}%."
        )

        return StrategyRegimeRecommendation(
            regime=regime,
            recommended_strategy=(
                winner.strategy_name
            ),
            confidence=confidence,
            trade_count=winner.trade_count,
            average_trade_return_percent=(
                winner.average_trade_return_percent
            ),
            total_return_percent=(
                winner.total_return_percent
            ),
            reason=reason,
        )

    @staticmethod
    def _confidence(
        trade_count: int,
        average_return: float,
    ) -> float:
        """
        Convert historical evidence into a bounded
        research confidence score.

        This is NOT the MarketRegime confidence.
        """

        if trade_count <= 0:
            return 0.0

        evidence_score = min(
            60.0,
            trade_count * 5.0,
        )

        performance_score = min(
            40.0,
            max(
                0.0,
                average_return * 10.0,
            ),
        )

        return round(
            min(
                100.0,
                evidence_score + performance_score,
            ),
            2,
        )
