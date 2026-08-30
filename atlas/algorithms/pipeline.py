"""
ATLAS Algorithm Pipeline.

Connects the registered trading algorithms to signal fusion without
coupling individual algorithms to the execution layer.
"""

from atlas.algorithms.base import AlgorithmSignal
from atlas.algorithms.fusion import SignalFusion
from atlas.algorithms.registry import AlgorithmRegistry


class AlgorithmPipeline:
    """Generate and fuse signals from registered algorithms."""

    def __init__(
        self,
        registry: AlgorithmRegistry,
        fusion: SignalFusion | None = None,
    ):
        self.registry = registry
        self.fusion = fusion or SignalFusion()

    def generate_signals(
        self,
        symbol: str,
        market_data: dict,
    ) -> list[AlgorithmSignal]:
        """Generate signals from every registered algorithm."""
        candles = market_data.get("candles", [])

        return self.registry.generate_signals(
            symbol,
            candles,
        )

    def analyze(
        self,
        symbol: str,
        market_data: dict,
    ):
        """Generate algorithm signals and fuse them."""
        signals = self.generate_signals(symbol, market_data)

        if not signals:
            return None, []

        fused = self.fusion.combine(signals)

        return fused, signals
