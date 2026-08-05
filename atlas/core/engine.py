"""
ATLAS Engine
"""

from atlas.core.config import AtlasConfig
from atlas.core.logger import get_logger


class AtlasEngine:

    def __init__(self):

        self.config = AtlasConfig()

        self.logger = get_logger("ATLAS")

    def start(self):

        self.logger.info("Starting ATLAS")

        self.logger.info(
            f"Version: {self.config.version}"
        )

        self.logger.info(
            f"Trading Mode: {self.config.trading_mode}"
        )

        self.logger.info(
            f"Capital Limit: {self.config.capital_limit}"
        )

        self.logger.info(
            "ATLAS is ready."
        )


if __name__ == "__main__":

    AtlasEngine().start()