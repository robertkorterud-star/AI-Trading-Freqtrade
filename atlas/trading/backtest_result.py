"""
Backtest Result

Contains the result of testing a trading strategy.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class BacktestResult:
    strategy_name: str
    symbol: str
    trades: int
    wins: int
    losses: int
    win_rate: float
    total_return: float
    profit_factor: float
    max_drawdown: float
