"""Continuous ATLAS runtime loop.

The loop owns scheduling only. Decision-making remains in AtlasEngine.
"""

import time

from atlas.core.config import AtlasConfig
from atlas.core.engine import AtlasEngine


class AtlasRuntimeLoop:
    """Run the canonical AtlasEngine cycle continuously."""

    def __init__(
        self,
        engine: AtlasEngine | None = None,
        interval_seconds: float = 30.0,
    ):
        self.engine = engine or AtlasEngine()
        self.interval_seconds = float(interval_seconds)
        if self.interval_seconds <= 0.0:
            raise ValueError("interval_seconds must be greater than zero")

    def run_forever(self):
        """Run AtlasEngine.start repeatedly until interrupted."""
        while True:
            started_at = time.monotonic()
            self.engine.start()
            elapsed = time.monotonic() - started_at
            time.sleep(max(0.0, self.interval_seconds - elapsed))


def run(config: AtlasConfig | None = None, interval_seconds: float = 30.0):
    """Start the continuous canonical ATLAS runtime."""
    AtlasRuntimeLoop(
        engine=AtlasEngine(config=config),
        interval_seconds=interval_seconds,
    ).run_forever()
