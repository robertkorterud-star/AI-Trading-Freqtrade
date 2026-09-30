"""ATLAS portfolio allocation and exposure management.

The portfolio layer owns aggregate capital allocation. It does not make
trading decisions and it does not place orders.
"""

from dataclasses import dataclass
import math
from collections.abc import Iterable


@dataclass(frozen=True, slots=True)
class PortfolioPosition:
    """Current marked-to-market position used by the portfolio layer."""

    symbol: str
    market_value: float

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        if not math.isfinite(self.market_value) or self.market_value < 0:
            raise ValueError("market_value must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class PortfolioAssessment:
    """Result of an aggregate portfolio allocation check."""

    allowed: bool
    requested_value: float
    approved_value: float
    current_exposure_value: float
    resulting_exposure_value: float
    current_exposure_pct: float
    resulting_exposure_pct: float
    available_capacity_value: float
    reasons: tuple[str, ...]


class PortfolioManager:
    """Manage aggregate portfolio exposure without executing trades.

    Per-trade sizing belongs to ``RiskManager``. This layer prevents a valid
    individual trade from creating an invalid aggregate portfolio exposure.
    """

    def __init__(
        self,
        max_exposure_pct: float = 100.0,
        max_single_position_pct: float = 20.0,
    ) -> None:
        for name, value in (
            ("max_exposure_pct", max_exposure_pct),
            ("max_single_position_pct", max_single_position_pct),
        ):
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")

        if max_single_position_pct > max_exposure_pct:
            raise ValueError(
                "max_single_position_pct must not exceed max_exposure_pct"
            )

        self.max_exposure_pct = float(max_exposure_pct)
        self.max_single_position_pct = float(max_single_position_pct)

    def assess(
        self,
        symbol: str,
        requested_value: float,
        equity: float,
        positions: Iterable[PortfolioPosition] = (),
    ) -> PortfolioAssessment:
        """Check whether a requested allocation fits the portfolio limits."""
        if not symbol.strip():
            raise ValueError("symbol must not be empty")
        if not math.isfinite(requested_value) or requested_value < 0:
            raise ValueError("requested_value must be finite and non-negative")
        if not math.isfinite(equity) or equity <= 0:
            raise ValueError("equity must be finite and greater than zero")

        position_list = tuple(positions)
        current_exposure = sum(position.market_value for position in position_list)
        existing_symbol_value = sum(
            position.market_value
            for position in position_list
            if position.symbol.strip().upper() == symbol.strip().upper()
        )

        max_exposure_value = equity * self.max_exposure_pct / 100.0
        max_single_value = equity * self.max_single_position_pct / 100.0
        available_capacity = max(0.0, max_exposure_value - current_exposure)
        single_position_capacity = max(0.0, max_single_value - existing_symbol_value)
        approved_value = min(
            requested_value,
            available_capacity,
            single_position_capacity,
        )

        allowed = (
            requested_value <= approved_value
            or math.isclose(
                requested_value,
                approved_value,
                rel_tol=1e-12,
                abs_tol=1e-12,
            )
        )
        resulting_exposure = current_exposure + approved_value
        reasons: list[str] = []

        if requested_value == 0:
            reasons.append("No additional allocation requested.")
        elif allowed:
            reasons.append("Portfolio allocation approved.")
        else:
            if requested_value > available_capacity + 1e-12:
                reasons.append("Requested allocation exceeds portfolio exposure capacity.")
            if requested_value > single_position_capacity + 1e-12:
                reasons.append("Requested allocation exceeds single-position capacity.")

        return PortfolioAssessment(
            allowed=allowed,
            requested_value=round(requested_value, 2),
            approved_value=round(approved_value, 2),
            current_exposure_value=round(current_exposure, 2),
            resulting_exposure_value=round(resulting_exposure, 2),
            current_exposure_pct=round(current_exposure / equity * 100.0, 4),
            resulting_exposure_pct=round(resulting_exposure / equity * 100.0, 4),
            available_capacity_value=round(min(available_capacity, single_position_capacity), 2),
            reasons=tuple(reasons),
        )
