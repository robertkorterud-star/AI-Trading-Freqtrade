"""
ATLAS Market Analysis Service.

Builds a unified MarketAnalysisSnapshot from market data,
indicator analysis, market regime analysis and multi-timeframe
analysis.

This service does not place trades.
"""

from atlas.trading.indicator_engine import IndicatorEngine
from atlas.trading.market_analysis_snapshot import (
    MarketAnalysisSnapshot,
)
from atlas.trading.market_regime import MarketRegimeAnalyzer
from atlas.trading.multi_timeframe_analysis import (
    MultiTimeframeAnalyzer,
)


class MarketAnalysisService:
    """Build unified market analysis snapshots."""

    def __init__(
        self,
        market_data,
        multi_timeframe_service,
        indicator_engine=None,
        regime_analyzer=None,
        multi_timeframe_analyzer=None,
    ):
        self.market_data = market_data
        self.multi_timeframe_service = (
            multi_timeframe_service
        )

        self.indicator_engine = (
            indicator_engine
            or IndicatorEngine()
        )

        self.regime_analyzer = (
            regime_analyzer
            or MarketRegimeAnalyzer()
        )

        self.multi_timeframe_analyzer = (
            multi_timeframe_analyzer
            or MultiTimeframeAnalyzer()
        )

    def analyze(
        self,
        symbol: str,
        candles: list[dict],
    ) -> MarketAnalysisSnapshot:

        indicators = self.indicator_engine.calculate(
            candles
        )

        regime = self.regime_analyzer.analyze(
            indicators
        )

        timeframe_data = (
            self.multi_timeframe_service.analyze(
                symbol
            )
        )

        multi_timeframe = (
            self.multi_timeframe_analyzer.analyze(
                symbol,
                timeframe_data,
            )
        )

        if indicators.data_quality in {
            "MISSING",
            "POOR",
        }:
            from dataclasses import replace

            multi_timeframe = replace(
                multi_timeframe,
                overall_signal="WAIT",
                confidence=0.0,
                alignment=0.0,
            )

        return MarketAnalysisSnapshot(
            symbol=symbol,
            indicators=indicators,
            regime=regime,
            multi_timeframe=multi_timeframe,
        )
