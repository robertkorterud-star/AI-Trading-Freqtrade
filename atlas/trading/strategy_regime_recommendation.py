"""
ATLAS Strategy Regime Recommendation.

Research-only recommendation of which strategy has
historically performed best within a market regime.

A historical winner is not automatically a robust winner.
The recommender can therefore return NO_ROBUST_WINNER
when the available evidence is too weak.

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
    evidence_strength: str
    robust_winner: bool
    trade_count: int
    win_rate_percent: float
    average_trade_return_percent: float
    total_return_percent: float
    reason: str


class StrategyRegimeRecommender:
    """
    Recommend the historically strongest strategy for a regime.

    A strategy must have sufficient evidence before it can be
    considered a robust winner.

    Confidence combines:
    - historical sample size
    - win rate
    - average trade performance

    Small samples are deliberately penalized.
    """

    MIN_ROBUST_TRADES = 10
    MIN_ROBUST_CONFIDENCE = 30.0

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
            return self._no_recommendation(
                regime,
                "No historical strategy trades "
                "were recorded for this regime.",
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

        win_rate = (
            winner.winning_trades
            / winner.trade_count
            * 100.0
        )

        confidence = self._confidence(
            trade_count=winner.trade_count,
            win_rate_percent=win_rate,
            average_return=(
                winner.average_trade_return_percent
            ),
        )

        evidence_strength = (
            self._evidence_strength(
                trade_count=winner.trade_count,
            )
        )

        robust_winner = (
            winner.trade_count
            >= self.MIN_ROBUST_TRADES
            and confidence
            >= self.MIN_ROBUST_CONFIDENCE
        )

        if robust_winner:
            recommended_strategy = (
                winner.strategy_name
            )

            reason = (
                f"{winner.strategy_name} is the strongest "
                f"historical strategy in {regime}, with "
                f"{winner.trade_count} trades, a "
                f"{win_rate:.1f}% win rate and an average "
                f"trade return of "
                f"{winner.average_trade_return_percent:.3f}%. "
                f"Evidence strength: "
                f"{evidence_strength}."
            )

        else:
            recommended_strategy = None

            reason = (
                f"{winner.strategy_name} is the historical "
                f"leader in {regime}, but the evidence is "
                f"not strong enough to identify a robust "
                f"winner. Historical leader: "
                f"{winner.trade_count} trades, "
                f"{win_rate:.1f}% win rate, "
                f"{winner.average_trade_return_percent:.3f}% "
                f"average trade return. "
                f"Evidence strength: "
                f"{evidence_strength}."
            )

        return StrategyRegimeRecommendation(
            regime=regime,
            recommended_strategy=recommended_strategy,
            confidence=confidence,
            evidence_strength=evidence_strength,
            robust_winner=robust_winner,
            trade_count=winner.trade_count,
            win_rate_percent=win_rate,
            average_trade_return_percent=(
                winner.average_trade_return_percent
            ),
            total_return_percent=(
                winner.total_return_percent
            ),
            reason=reason,
        )

    @staticmethod
    def _no_recommendation(
        regime: str,
        reason: str,
    ) -> StrategyRegimeRecommendation:

        return StrategyRegimeRecommendation(
            regime=regime,
            recommended_strategy=None,
            confidence=0.0,
            evidence_strength="VERY_WEAK",
            robust_winner=False,
            trade_count=0,
            win_rate_percent=0.0,
            average_trade_return_percent=0.0,
            total_return_percent=0.0,
            reason=reason,
        )

    @staticmethod
    def _confidence(
        trade_count: int,
        win_rate_percent: float,
        average_return: float,
    ) -> float:
        """
        Calculate bounded research confidence.

        Sample size uses:

            n / (n + 10)

        so small samples are strongly discounted.
        """

        if trade_count <= 0:
            return 0.0

        sample_factor = (
            trade_count
            / (trade_count + 10.0)
        )

        win_rate_score = max(
            0.0,
            min(
                100.0,
                win_rate_percent,
            ),
        )

        performance_score = min(
            100.0,
            max(
                0.0,
                average_return * 10.0,
            ),
        )

        combined_score = (
            performance_score * 0.5
            + win_rate_score * 0.5
        )

        confidence = (
            sample_factor
            * combined_score
        )

        return round(
            min(
                100.0,
                max(
                    0.0,
                    confidence,
                ),
            ),
            2,
        )

    @staticmethod
    def _evidence_strength(
        trade_count: int,
    ) -> str:

        if trade_count < 3:
            return "VERY_WEAK"

        if trade_count < 10:
            return "WEAK"

        if trade_count < 20:
            return "MODERATE"

        return "STRONG"
