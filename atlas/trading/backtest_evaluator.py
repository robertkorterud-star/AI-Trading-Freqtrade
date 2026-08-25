from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class BacktestAssessment:
    """Interpretation of a backtest result."""

    status: str
    reason: str


class BacktestEvaluator:
    """Classify backtest quality without placing trades."""

    PASS_MIN_PROFIT_FACTOR = 1.20
    PASS_MAX_DRAWDOWN = 25.0

    REJECT_MAX_PROFIT_FACTOR = 1.0
    REJECT_MAX_DRAWDOWN = 40.0

    @classmethod
    def assess(
        cls,
        result,
    ) -> BacktestAssessment:
        """Return PASS, REJECT or INCONCLUSIVE."""

        total_return = float(
            result.total_return
        )
        profit_factor = float(
            result.profit_factor
        )
        max_drawdown = float(
            result.max_drawdown
        )

        if total_return <= 0.0:
            return BacktestAssessment(
                status="REJECT",
                reason=(
                    "Backtest lost money over the "
                    "tested period."
                ),
            )

        if profit_factor < cls.REJECT_MAX_PROFIT_FACTOR:
            return BacktestAssessment(
                status="REJECT",
                reason=(
                    "Profit factor is below 1.0, "
                    "so losses outweigh profits."
                ),
            )

        if max_drawdown > cls.REJECT_MAX_DRAWDOWN:
            return BacktestAssessment(
                status="REJECT",
                reason=(
                    "Maximum drawdown is too high "
                    "for the current quality threshold."
                ),
            )

        if (
            profit_factor >= cls.PASS_MIN_PROFIT_FACTOR
            and max_drawdown <= cls.PASS_MAX_DRAWDOWN
        ):
            return BacktestAssessment(
                status="PASS",
                reason=(
                    "Positive return, strong profit "
                    "factor and controlled drawdown."
                ),
            )

        return BacktestAssessment(
            status="INCONCLUSIVE",
            reason=(
                "The strategy is profitable but does "
                "not yet meet ATLAS quality thresholds."
            ),
        )
