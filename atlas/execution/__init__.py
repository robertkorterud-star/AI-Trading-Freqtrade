"""ATLAS execution boundary.

Execution is deliberately isolated from decision, risk, and portfolio logic.
Broker/exchange implementations belong behind the interfaces in this package.
"""

from atlas.execution.binance_testnet import BinanceTestnetExecutionAdapter
from atlas.execution.dryrun import DryRunExecutionAdapter
from atlas.execution.models import ExecutionRequest, ExecutionResult, ExecutionStatus
from atlas.execution.protocol import ExecutionAdapter, ExecutionEngine
from atlas.execution.service import DecisionExecutionService

__all__ = [
    "BinanceTestnetExecutionAdapter",
    "DecisionExecutionService",
    "DryRunExecutionAdapter",
    "ExecutionAdapter",
    "ExecutionEngine",
    "ExecutionRequest",
    "ExecutionResult",
    "ExecutionStatus",
]
