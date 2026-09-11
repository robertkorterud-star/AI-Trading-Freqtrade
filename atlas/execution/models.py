"""Models for the ATLAS execution boundary."""

from dataclasses import dataclass
from enum import Enum

from atlas.models.action import Action


class ExecutionStatus(str, Enum):
    """Outcome of an execution request."""

    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    SIMULATED = "SIMULATED"


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    """Execution intent produced from an approved ATLAS decision."""

    symbol: str
    action: Action
    quantity: float
    price: float | None = None
    analysis_snapshot_id: int | None = None

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        if not isinstance(self.action, Action):
            raise ValueError("action must be an Action")
        if self.action not in {Action.BUY, Action.SELL}:
            raise ValueError("execution requires BUY or SELL action")
        if self.quantity <= 0:
            raise ValueError("quantity must be greater than zero")
        if self.price is not None and self.price <= 0:
            raise ValueError("price must be greater than zero when provided")
        if self.analysis_snapshot_id is not None and self.analysis_snapshot_id <= 0:
            raise ValueError("analysis_snapshot_id must be greater than zero when provided")


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Broker-independent result returned by an execution adapter."""

    status: ExecutionStatus
    symbol: str
    action: Action
    quantity: float
    message: str = ""
    external_order_id: str | None = None
