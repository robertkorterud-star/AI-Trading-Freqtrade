"""
ATLAS Strategy Memory History Record.

Immutable representation of one historical strategy-memory
observation belonging to a specific research run.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class StrategyMemoryHistoryRecord:
    """One immutable historical research observation."""

    research_run_id: str
    symbol: str
    regime: str
    strategy_name: str
    trade_count: int
    winning_trades: int
    losing_trades: int
    win_rate_percent: float
    average_trade_return_percent: float
    total_return_percent: float
    evidence_strength: str
    robust_winner: bool
    recorded_at: datetime
