"""ATLAS execution boundary.

Execution is deliberately isolated from decision, risk, and portfolio logic.
Broker/exchange implementations belong behind the interfaces in this package.
"""

from atlas.execution.models import ExecutionRequest, ExecutionResult, ExecutionStatus
from atlas.execution.protocol import ExecutionAdapter, ExecutionEngine

__all__ = [
    "ExecutionAdapter",
    "ExecutionEngine",
    "ExecutionRequest",
    "ExecutionResult",
    "ExecutionStatus",
]
