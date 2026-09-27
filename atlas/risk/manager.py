"""ATLAS risk management boundary.

Risk management evaluates an already-approved direction and constrains the
capital that may be exposed. It never places orders or changes the decision
itself.
"""

from dataclasses import dataclass
import math

from atlas.models.action import Action


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    """Result of applying ATLAS risk constraints to a decision."""

    action: Action
    allowed: bool
    risk_level: str
    position_size: float
    position_value: float
    stop_loss_price: float | None
    take_profit_price: float | None
    reasons: tuple[str, ...]


class RiskManager:
    """Apply deterministic capital and exposure constraints."""

    def __init__(
        self,
        risk_per_trade_pct: float = 1.0,
        max_position_pct: float = 20.0,
        max_exposure_pct: float = 100.0,
        stop_loss_pct: float = 2.0,
        take_profit_pct: float = 4.0,
        max_drawdown_pct: float = 20.0,
    ) -> None:
        values = {
            "risk_per_trade_pct": risk_per_trade_pct,
            "max_position_pct": max_position_pct,
            "max_exposure_pct": max_exposure_pct,
            "stop_loss_pct": stop_loss_pct,
            "take_profit_pct": take_profit_pct,
            "max_drawdown_pct": max_drawdown_pct,
        }
        if any(not math.isfinite(value) or value < 0 for value in values.values()):
            raise ValueError("risk parameters must be finite and non-negative")
        if stop_loss_pct == 0:
            raise ValueError("stop_loss_pct must be greater than zero")
        if max_position_pct > max_exposure_pct:
            raise ValueError("max_position_pct cannot exceed max_exposure_pct")

        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_position_pct = max_position_pct
        self.max_exposure_pct = max_exposure_pct
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_drawdown_pct = max_drawdown_pct

    def assess(
        self,
        action: Action,
        price: float,
        equity: float,
        current_exposure_pct: float = 0.0,
        drawdown_pct: float = 0.0,
        current_position: float = 0.0,
    ) -> RiskAssessment:
        """Assess whether a decision may expose capital."""
        if not isinstance(action, Action):
            action = Action(action)

        numeric = {
            "price": price,
            "equity": equity,
            "current_exposure_pct": current_exposure_pct,
            "drawdown_pct": drawdown_pct,
            "current_position": current_position,
        }
        if any(not math.isfinite(value) for value in numeric.values()):
            raise ValueError("risk inputs must be finite")
        if price <= 0 or equity <= 0:
            raise ValueError("price and equity must be greater than zero")
        if current_exposure_pct < 0 or drawdown_pct < 0 or current_position < 0:
            raise ValueError("exposure, drawdown, and current position must be non-negative")

        reasons: list[str] = []
        if action is Action.HOLD or action is Action.WATCH:
            return RiskAssessment(
                action=action,
                allowed=True,
                risk_level="NONE",
                position_size=0.0,
                position_value=0.0,
                stop_loss_price=None,
                take_profit_price=None,
                reasons=("No new market exposure requested.",),
            )

        if action is Action.SELL:
            if current_position <= 0.0:
                return RiskAssessment(
                    action=action,
                    allowed=False,
                    risk_level="BLOCKED",
                    position_size=0.0,
                    position_value=0.0,
                    stop_loss_price=None,
                    take_profit_price=None,
                    reasons=("No open position available to sell.",),
                )

            return RiskAssessment(
                action=action,
                allowed=True,
                risk_level="LOW",
                position_size=current_position,
                position_value=current_position * price,
                stop_loss_price=None,
                take_profit_price=None,
                reasons=("SELL reduces the existing long position.",),
            )

        if drawdown_pct >= self.max_drawdown_pct:
            return RiskAssessment(
                action=action,
                allowed=False,
                risk_level="BLOCKED",
                position_size=0.0,
                position_value=0.0,
                stop_loss_price=None,
                take_profit_price=None,
                reasons=("Maximum drawdown limit reached.",),
            )

        remaining_exposure_pct = self.max_exposure_pct - current_exposure_pct
        if remaining_exposure_pct <= 0:
            return RiskAssessment(
                action=action,
                allowed=False,
                risk_level="BLOCKED",
                position_size=0.0,
                position_value=0.0,
                stop_loss_price=None,
                take_profit_price=None,
                reasons=("Maximum portfolio exposure reached.",),
            )

        position_pct = min(self.max_position_pct, remaining_exposure_pct)
        max_position_value = equity * position_pct / 100.0
        if action is Action.BUY:
            existing_position_value = current_position * price
            max_position_value = max(
                0.0,
                max_position_value - existing_position_value,
            )
        risk_budget = equity * self.risk_per_trade_pct / 100.0
        stop_distance = price * self.stop_loss_pct / 100.0
        size_by_risk = risk_budget / stop_distance
        position_size = min(max_position_value / price, size_by_risk)
        position_value = position_size * price

        if position_size <= 0:
            return RiskAssessment(
                action=action,
                allowed=False,
                risk_level="BLOCKED",
                position_size=0.0,
                position_value=0.0,
                stop_loss_price=None,
                take_profit_price=None,
                reasons=("Risk constraints permit no position size.",),
            )

        if action is Action.BUY:
            stop_loss = price * (1 - self.stop_loss_pct / 100.0)
            take_profit = price * (1 + self.take_profit_pct / 100.0)
        else:
            stop_loss = price * (1 + self.stop_loss_pct / 100.0)
            take_profit = price * (1 - self.take_profit_pct / 100.0)

        reasons.append(f"Position capped at {position_value / equity * 100:.1f}% of equity.")
        reasons.append(f"Risk budget is {self.risk_per_trade_pct:.1f}% of equity.")
        reasons.append(f"Stop loss distance is {self.stop_loss_pct:.1f}%.")

        risk_level = "LOW" if drawdown_pct < self.max_drawdown_pct * 0.5 else "MODERATE"
        return RiskAssessment(
            action=action,
            allowed=True,
            risk_level=risk_level,
            position_size=position_size,
            position_value=position_value,
            stop_loss_price=stop_loss,
            take_profit_price=take_profit,
            reasons=tuple(reasons),
        )
