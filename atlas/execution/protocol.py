"""Broker-independent execution interfaces."""

from typing import Protocol

from atlas.execution.models import ExecutionRequest, ExecutionResult


class ExecutionAdapter(Protocol):
    """External execution implementation supplied by a broker/exchange."""

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Submit an execution request to the external venue."""
        ...


class ExecutionEngine:
    """Thin ATLAS boundary between approved decisions and execution adapters."""

    def __init__(self, adapter: ExecutionAdapter) -> None:
        self.adapter = adapter

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Delegate an already-approved execution request to the adapter."""
        return self.adapter.execute(request)
