"""
ATLAS Database Configuration
"""

from dataclasses import dataclass


@dataclass(slots=True)
class DatabaseConfig:
    """Configuration for ATLAS database storage."""

    path: str = "atlas/data/atlas.db"
