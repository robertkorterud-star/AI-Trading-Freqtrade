"""
ATLAS User Settings
"""

from dataclasses import dataclass


@dataclass
class UserSettings:
    """Global user settings."""

    currency: str = "USD"

    language: str = "en"

    theme: str = "dark"

    default_symbol: str = "BTC-USD"


settings = UserSettings()