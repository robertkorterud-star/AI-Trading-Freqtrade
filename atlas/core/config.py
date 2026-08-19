"""
Global configuration for ATLAS.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class AtlasConfig:
    """
    Global configuration used by the ATLAS engine.
    """

    project_name: str = "ATLAS"

    version: str = "0.1 Alpha"

    trading_mode: str = "advisor"

    language: str = "no"

    ai_provider: str = "openai"

    paper_trading: bool = True

    debug: bool = True

    max_open_trades: int = 3

    capital_limit: float = 5000.0

    agent_performance_storage: str = (
        "atlas/data/agent_performance.json"
    )
