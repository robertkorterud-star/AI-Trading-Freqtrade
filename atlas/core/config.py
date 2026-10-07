"""
Global configuration for ATLAS.
"""

from dataclasses import dataclass, field
import os


@dataclass(slots=True)
class AtlasConfig:
    """
    Global configuration used by the ATLAS engine.
    """

    project_name: str = "ATLAS"

    version: str = "0.1 Alpha"

    trading_mode: str = "advisor"

    language: str = "no"

    ai_provider: str = "ollama"

    paper_trading: bool = True

    debug: bool = True

    max_open_trades: int = 3

    capital_limit: float = 5000.0

    # Percentage price drop required before ATLAS may consider
    # an additional accumulation entry for an existing position.
    accumulation_drop_pct: float = 2.0

    agent_performance_storage: str = (
        "atlas/data/agent_performance.json"
    )

    database_path: str = field(
        default_factory=lambda: os.environ.get(
            "ATLAS_DATABASE_PATH",
            "atlas/data/atlas.db",
        )
    )

    binance_api_key: str | None = field(
        default_factory=lambda: os.environ.get("BINANCE_API_KEY")
    )

    load_persisted_settings: bool = False
