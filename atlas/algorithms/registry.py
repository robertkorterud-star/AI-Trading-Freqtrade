"""ATLAS trading algorithm registry."""

from atlas.algorithms.base import AlgorithmSignal, TradingAlgorithm


class AlgorithmRegistry:
    """Registry for ATLAS trading algorithms."""

    def __init__(self):
        self._algorithms: dict[str, TradingAlgorithm] = {}

    def register(self, algorithm: TradingAlgorithm) -> None:
        """Register an algorithm by its unique name."""

        if algorithm.name in self._algorithms:
            raise ValueError(
                f"algorithm already registered: {algorithm.name}"
            )

        self._algorithms[algorithm.name] = algorithm

    def get(self, name: str) -> TradingAlgorithm:
        """Return a registered algorithm by name."""

        try:
            return self._algorithms[name]
        except KeyError as exc:
            raise KeyError(
                f"algorithm not registered: {name}"
            ) from exc

    def all(self) -> tuple[TradingAlgorithm, ...]:
        """Return all registered algorithms in registration order."""

        return tuple(self._algorithms.values())

    def names(self) -> tuple[str, ...]:
        """Return registered algorithm names."""

        return tuple(self._algorithms.keys())

    def generate_signals(
        self,
        symbol: str,
        candles: list[dict],
    ) -> list[AlgorithmSignal]:
        """Generate one signal from every registered algorithm."""

        return [
            algorithm.generate_signal(symbol, candles)
            for algorithm in self._algorithms.values()
        ]
