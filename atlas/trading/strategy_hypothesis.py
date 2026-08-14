"""
Strategy Hypothesis

Represents a trading strategy hypothesis discovered by ATLAS.
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class StrategyHypothesis:
    name: str
    symbol: str
    timeframe: str
    entry_rule: str
    exit_rule: str
    stop_loss: str
    take_profit: str
    source: str
    reasoning: list[str] = field(default_factory=list)
