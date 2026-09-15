"""
ATLAS Position & Exit Engine

Determines position sizing and exit actions across multiple trading
horizons. This module is deliberately independent from any single
strategy so ATLAS can manage intraday, swing and longer-term positions.
"""

from dataclasses import dataclass
from enum import Enum


class PositionAction(str, Enum):
    ENTER = "enter"
    HOLD = "hold"
    REDUCE = "reduce"
    EXIT = "exit"


@dataclass(frozen=True)
class PositionContext:
    """Current state of an existing or potential position."""

    current_position: float = 0.0
    entry_price: float | None = None
    current_price: float | None = None
    peak_price: float | None = None
    confidence: float = 0.0
    risk_score: float = 0.0


@dataclass(frozen=True)
class PositionDecision:
    """Position management decision produced by ATLAS."""

    action: PositionAction
    target_position: float
    size_fraction: float
    reason: str


class PositionExitEngine:
    """
    Converts a directional decision into position-management actions.

    Position sizes are expressed as fractions of the configured maximum
    position. Positive values represent long exposure.
    """

    def __init__(
        self,
        max_position: float = 1.0,
        entry_confidence: float = 0.65,
        reduce_confidence: float = 0.45,
        exit_confidence: float = 0.30,
        stop_loss: float = 0.08,
        trailing_stop: float = 0.10,
        accumulation_drop_pct: float = 2.0,
    ):
        if max_position <= 0.0:
            raise ValueError("max_position must be greater than zero")

        if not 0.0 <= entry_confidence <= 1.0:
            raise ValueError("entry_confidence must be between 0 and 1")

        if not 0.0 <= reduce_confidence <= 1.0:
            raise ValueError("reduce_confidence must be between 0 and 1")

        if not 0.0 <= exit_confidence <= 1.0:
            raise ValueError("exit_confidence must be between 0 and 1")

        if not 0.0 <= stop_loss <= 1.0:
            raise ValueError("stop_loss must be between 0 and 1")

        if not 0.0 <= trailing_stop <= 1.0:
            raise ValueError("trailing_stop must be between 0 and 1")

        if not 0.0 <= accumulation_drop_pct <= 100.0:
            raise ValueError("accumulation_drop_pct must be between 0 and 100")

        self.max_position = max_position
        self.entry_confidence = entry_confidence
        self.reduce_confidence = reduce_confidence
        self.exit_confidence = exit_confidence
        self.stop_loss = stop_loss
        self.trailing_stop = trailing_stop
        self.accumulation_drop_pct = accumulation_drop_pct

    def decide(
        self,
        action,
        context: PositionContext,
    ) -> PositionDecision:
        """
        Manage a long position from an upstream BUY/HOLD/SELL decision.

        A BUY with sufficient confidence opens or maintains exposure.
        An existing position may receive another entry only after the
        configured accumulation price drop has been reached.
        A weakening BUY reduces an existing position.
        SELL exits when confidence is sufficiently strong and reduces
        exposure when the sell signal is weaker.

        Independent protective exits take priority over directional
        signals.
        """

        action_value = getattr(action, "value", action)
        action_value = str(action_value).strip().lower()

        confidence = self._clamp(context.confidence)
        risk = self._clamp(context.risk_score)

        protective_exit = self._protective_exit(context)

        if protective_exit is not None:
            return protective_exit

        if action_value == "buy":
            if confidence < self.entry_confidence:
                if context.current_position > 0.0:
                    target = context.current_position * 0.75
                    return PositionDecision(
                        action=PositionAction.REDUCE,
                        target_position=target,
                        size_fraction=self._fraction(target),
                        reason="buy confidence too weak to maintain full position",
                    )

                return PositionDecision(
                    action=PositionAction.HOLD,
                    target_position=0.0,
                    size_fraction=0.0,
                    reason="buy confidence below entry threshold",
                )

            target = self._entry_size(confidence, risk)

            if context.current_position <= 0.0:
                return PositionDecision(
                    action=PositionAction.ENTER,
                    target_position=target,
                    size_fraction=self._fraction(target),
                    reason="buy signal passed position sizing gate",
                )

            if self._accumulation_allowed(context):
                return PositionDecision(
                    action=PositionAction.ENTER,
                    target_position=target,
                    size_fraction=self._fraction(target),
                    reason="buy signal passed accumulation price-drop gate",
                )

            return PositionDecision(
                action=PositionAction.HOLD,
                target_position=context.current_position,
                size_fraction=self._fraction(context.current_position),
                reason="existing position has not reached accumulation price-drop threshold",
            )

        if action_value == "sell":
            if context.current_position <= 0.0:
                return PositionDecision(
                    action=PositionAction.HOLD,
                    target_position=0.0,
                    size_fraction=0.0,
                    reason="no long position to exit",
                )

            if confidence >= self.exit_confidence and confidence >= self.entry_confidence:
                return PositionDecision(
                    action=PositionAction.EXIT,
                    target_position=0.0,
                    size_fraction=0.0,
                    reason="strong sell signal passed exit threshold",
                )

            if confidence >= self.reduce_confidence:
                target = context.current_position * 0.50

                return PositionDecision(
                    action=PositionAction.REDUCE,
                    target_position=target,
                    size_fraction=self._fraction(target),
                    reason="moderate sell signal reduced position",
                )

            return PositionDecision(
                action=PositionAction.HOLD,
                target_position=context.current_position,
                size_fraction=self._fraction(context.current_position),
                reason="sell confidence too weak to reduce position",
            )

        if context.current_position > 0.0:
            return PositionDecision(
                action=PositionAction.HOLD,
                target_position=context.current_position,
                size_fraction=self._fraction(context.current_position),
                reason="no directional change",
            )

        return PositionDecision(
            action=PositionAction.HOLD,
            target_position=0.0,
            size_fraction=0.0,
            reason="no position and no entry signal",
        )

    def _accumulation_allowed(self, context: PositionContext) -> bool:
        if context.entry_price is None or context.current_price is None:
            return False

        threshold = context.entry_price * (
            1.0 - self.accumulation_drop_pct / 100.0
        )
        return context.current_price <= threshold

    def _entry_size(self, confidence: float, risk: float) -> float:
        """
        Scale position size with confidence and inversely with risk.

        A high-confidence, low-risk signal can approach max_position.
        """
        confidence_factor = max(
            0.0,
            (confidence - self.entry_confidence)
            / max(1.0 - self.entry_confidence, 1e-9),
        )

        risk_factor = 1.0 - risk

        minimum_factor = 0.25
        factor = minimum_factor + (
            (1.0 - minimum_factor)
            * confidence_factor
            * risk_factor
        )

        return min(
            self.max_position,
            self.max_position * factor,
        )

    def _protective_exit(
        self,
        context: PositionContext,
    ) -> PositionDecision | None:
        if context.current_position <= 0.0:
            return None

        if context.entry_price is not None and context.current_price is not None:
            if context.current_price <= context.entry_price * (
                1.0 - self.stop_loss
            ):
                return PositionDecision(
                    action=PositionAction.EXIT,
                    target_position=0.0,
                    size_fraction=0.0,
                    reason="stop loss triggered",
                )

        if context.peak_price is not None and context.current_price is not None:
            if context.current_price <= context.peak_price * (
                1.0 - self.trailing_stop
            ):
                return PositionDecision(
                    action=PositionAction.EXIT,
                    target_position=0.0,
                    size_fraction=0.0,
                    reason="trailing stop triggered",
                )

        return None

    def _fraction(self, position: float) -> float:
        if self.max_position <= 0.0:
            return 0.0

        return max(
            0.0,
            min(1.0, position / self.max_position),
        )

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))
