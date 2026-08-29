"""ATLAS algorithmic trading strategies."""

from atlas.algorithms.base import AlgorithmSignal, TradingAlgorithm
from atlas.algorithms.momentum import IntradayMomentumAlgorithm
from atlas.algorithms.mean_reversion import IntradayMeanReversionAlgorithm
from atlas.algorithms.breakout import IntradayBreakoutAlgorithm
from atlas.algorithms.vwap import IntradayVWAPAlgorithm
from atlas.algorithms.registry import AlgorithmRegistry
from atlas.algorithms.fusion import FusionResult, SignalFusion
from atlas.algorithms.regime import MarketRegime, MarketRegimeEngine, MarketRegimeResult

__all__ = [
    "AlgorithmSignal",
    "TradingAlgorithm",
    "IntradayMomentumAlgorithm",
    "AlgorithmRegistry",
    "IntradayMeanReversionAlgorithm",
    "IntradayBreakoutAlgorithm",
    "IntradayVWAPAlgorithm",
    "FusionResult",
    "SignalFusion",
    "MarketRegime",
    "MarketRegimeEngine",
    "MarketRegimeResult",
]
