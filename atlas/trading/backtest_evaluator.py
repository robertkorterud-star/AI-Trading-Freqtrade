from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class BacktestAssessment:
    """Interpretation of a backtest result."""

    status: str
    reason: str
    next_focus: tuple[str, ...] = ()


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
        strategy_name: str = "",
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
            if "rsi" in strategy_name.lower():
                next_focus = (
                    "moving average",
                    "golden cross",
                    "breakout",
                    "momentum",
                )
            elif "moving average" in strategy_name.lower():
                next_focus = (
                    "rsi",
                    "breakout",
                    "momentum",
                )
            else:
                next_focus = (
                    "rsi",
                    "moving average",
                    "breakout",
                    "momentum",
                )

            return BacktestAssessment(
                status="REJECT",
                reason=(
                    "Backtest lost money over the "
                    "tested period."
                ),
                next_focus=next_focus,
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
