"""Dry-run execution adapter for ATLAS.

This adapter is the safe execution implementation for development and
validation. It records execution requests in memory and never contacts a
broker, exchange, or order API.
"""

from atlas.execution.models import ExecutionRequest, ExecutionResult, ExecutionStatus


class DryRunExecutionAdapter:
    """Simulate execution without sending any live order."""

    def __init__(self) -> None:
        self.requests: list[ExecutionRequest] = []

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Record the request and return a simulated execution result."""
        self.requests.append(request)
        return ExecutionResult(
            status=ExecutionStatus.SIMULATED,
            symbol=request.symbol,
            action=request.action,
            quantity=request.quantity,
            message="dry-run execution; no live order was submitted",
        )
