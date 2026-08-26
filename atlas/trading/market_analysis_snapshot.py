"""
ATLAS unified market analysis snapshot.

Combines indicator, regime and multi-timeframe analysis
into one immutable-style analysis object.

This layer contains context only. It does not place trades.
"""

from dataclasses import dataclass

from atlas.trading.indicator_engine import IndicatorSnapshot
from atlas.trading.market_regime import MarketRegime
from atlas.trading.multi_timeframe_analysis import (
    MultiTimeframeAnalysis,
)


@dataclass(slots=True)
class MarketAnalysisSnapshot:
    symbol: str
    indicators: IndicatorSnapshot
    regime: MarketRegime
    multi_timeframe: MultiTimeframeAnalysis

    @property
    def overall_signal(self) -> str:
        """Return the current multi-timeframe signal."""
        return self.multi_timeframe.overall_signal

    @property
    def confidence(self) -> float:
        """Return the current multi-timeframe confidence."""
        return self.multi_timeframe.confidence

    @property
    def alignment(self) -> float:
        """Return the current multi-timeframe alignment."""
        return self.multi_timeframe.alignment

    @property
    def regime_name(self) -> str:
        """Return the detected market regime."""
        return self.regime.regime

    @property
    def data_quality(self) -> str:
        """Return the weakest relevant data quality."""
        qualities = [
            self.indicators.data_quality,
            self.regime.volatility_level,
            self.multi_timeframe.data_quality,
        ]

        if "MISSING" in qualities:
            return "MISSING"

        if "POOR" in qualities:
            return "POOR"

        if "PARTIAL" in qualities:
            return "PARTIAL"

        return "GOOD"
