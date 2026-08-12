"""
ATLAS Settings Service
"""

from atlas.core.config import AtlasConfig


class SettingsService:
    """Manage safe ATLAS trading settings."""

    def __init__(self):
        self.config = AtlasConfig()

    def get_config(self):
        return self.config

    def get_trading_status(self):
        return {
            "mode": self.config.trading_mode,
            "paper_trading": self.config.paper_trading,
            "live_orders": False,
        }

    def set_trading_mode(self, mode):
        if mode == "advisor":
            self.config.trading_mode = "advisor"
            self.config.paper_trading = True
            return

        if mode == "paper":
            self.config.trading_mode = "paper"
            self.config.paper_trading = True
            return

        raise ValueError(
            "Unsupported trading mode. "
            "Use 'advisor' or 'paper'."
        )
