from atlas.execution import (
    DryRunExecutionAdapter,
    ExecutionEngine,
    ExecutionRequest,
    ExecutionStatus,
)
from atlas.models.action import Action


def test_dryrun_adapter_never_creates_live_order() -> None:
    adapter = DryRunExecutionAdapter()
    engine = ExecutionEngine(adapter)
    request = ExecutionRequest("BTC/USDT", Action.BUY, 0.25, price=100_000.0)

    result = engine.execute(request)

    assert result.status is ExecutionStatus.SIMULATED
    assert result.external_order_id is None
    assert result.message == "dry-run execution; no live order was submitted"
    assert adapter.requests == [request]


def test_dryrun_adapter_supports_sell() -> None:
    adapter = DryRunExecutionAdapter()
    request = ExecutionRequest("BTC/USDT", Action.SELL, 0.1)

    result = adapter.execute(request)

    assert result.status is ExecutionStatus.SIMULATED
    assert result.action is Action.SELL
    assert result.quantity == 0.1
