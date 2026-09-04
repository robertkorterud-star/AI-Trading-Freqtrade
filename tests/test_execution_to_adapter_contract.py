from atlas.execution.models import ExecutionRequest, ExecutionResult, ExecutionStatus
from atlas.execution.protocol import ExecutionEngine
from atlas.models.action import Action


class RecordingAdapter:
    def __init__(self):
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return ExecutionResult(
            status=ExecutionStatus.SIMULATED,
            symbol=request.symbol,
            action=request.action,
            quantity=request.quantity,
            message="recorded",
        )


def test_execution_engine_passes_exact_request_to_adapter():
    adapter = RecordingAdapter()
    engine = ExecutionEngine(adapter)
    request = ExecutionRequest(
        symbol="BTC-USD",
        action=Action.BUY,
        quantity=0.1,
        price=100_000.0,
    )

    result = engine.execute(request)

    assert adapter.requests == [request]
    assert result.status is ExecutionStatus.SIMULATED
    assert result.symbol == request.symbol
    assert result.action is request.action
    assert result.quantity == request.quantity


def test_execution_request_rejects_hold_before_adapter_boundary():
    adapter = RecordingAdapter()
    engine = ExecutionEngine(adapter)

    try:
        request = ExecutionRequest(
            symbol="BTC-USD",
            action=Action.HOLD,
            quantity=0.1,
        )
    except ValueError as exc:
        assert "buy or sell" in str(exc).lower()
    else:
        engine.execute(request)
        raise AssertionError("HOLD must never become an execution request")

    assert adapter.requests == []
