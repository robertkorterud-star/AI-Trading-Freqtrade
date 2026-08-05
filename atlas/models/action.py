"""
ATLAS Actions

Defines all possible decisions that can be made by the system.
"""

from enum import Enum


class Action(str, Enum):
    """Supported actions inside ATLAS."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    WATCH = "WATCH"