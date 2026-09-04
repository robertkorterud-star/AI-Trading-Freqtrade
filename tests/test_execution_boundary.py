import pytest

from atlas.execution import (
    ExecutionEngine,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)
from atlas.models.action import Action


class FakeAdapter:
    def __init__(self) -> None:
        self.requests = []

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        self.requests.append(request)
        return ExecutionResult(
            status=ExecutionStatus.SIMULATED,
            symbol=request.symbol,
            action=request.action,
            quantity=request.quantity,
            message="simulation",
            external_order_id="sim-1",
        )


def test_execution_engine_delegates_to_external_adapter() -> None:
    adapter = FakeAdapter()
    engine = ExecutionEngine(adapter)
    request = ExecutionRequest("BTC/USDT", Action.BUY, 0.25, price=100_000.0)

    result = engine.execute(request)

    assert adapter.requests == [request]
    assert result.status is ExecutionStatus.SIMULATED
    assert result.external_order_id == "sim-1"


def test_execution_request_rejects_hold() -> None:
    with pytest.raises(ValueError, match="BUY or SELL"):
        ExecutionRequest("BTC/USDT", Action.HOLD, 1.0)


def test_execution_request_rejects_non_positive_quantity() -> None:
    with pytest.raises(ValueError, match="quantity"):
        ExecutionRequest("BTC/USDT", Action.BUY, 0.0)
