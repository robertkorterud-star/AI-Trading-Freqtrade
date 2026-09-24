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
        market_data,
    ) -> list[AlgorithmSignal]:
        """Generate signals from every registered algorithm."""
        if isinstance(market_data, dict):
            base_candles = market_data.get("candles", [])
            timeframe_candles = {}
        else:
            base_candles = market_data.candles
            timeframe_candles = market_data.timeframe_candles

        signals: list[AlgorithmSignal] = []

        for algorithm in self.registry.all():
            candles = timeframe_candles.get(
                getattr(algorithm, "timeframe", None),
                base_candles,
            )

            try:
                signal = algorithm.generate_signal(
                    symbol,
                    candles,
                )
            except ValueError as exc:
                message = str(exc)

                if (
                    message.startswith("at least ")
                    and message.endswith(" candles are required")
                ):
                    continue

                raise

            signals.append(signal)

        return signals

    def analyze(
        self,
        symbol: str,
        market_data,
    ):
        """Generate algorithm signals and fuse them."""
        signals = self.generate_signals(symbol, market_data)

        if not signals:
            return None, []

        fused = self.fusion.combine(signals)

        return fused, signals
