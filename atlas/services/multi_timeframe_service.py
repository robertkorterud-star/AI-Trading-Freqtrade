"""
Multi-timeframe market analysis.

Builds current directional signals across:
4h, 1h, 15m, 5m and 1m.

This service does NOT place trades.
"""

from atlas.adapters.historical_market_data import (
    HistoricalMarketDataAdapter,
)
from atlas.trading.indicators import (
    calculate_rsi,
    calculate_sma,
)
from atlas.trading.multi_timeframe_analysis import (
    MultiTimeframeAnalysis,
    MultiTimeframeAnalyzer,
)


class MultiTimeframeService:
    """Calculate current multi-timeframe signals."""

    CONFIG = {
        "4h": {
            "period": "60d",
            "interval": "4h",
        },
        "1h": {
            "period": "30d",
            "interval": "1h",
        },
        "15m": {
            "period": "5d",
            "interval": "15m",
        },
        "5m": {
            "period": "2d",
            "interval": "5m",
        },
        "1m": {
            "period": "1d",
            "interval": "1m",
        },
    }

    def __init__(
        self,
        market_data=None,
        analyzer=None,
    ) -> None:

        self.market_data = (
            market_data
            if market_data is not None
            else HistoricalMarketDataAdapter()
        )

        self.analyzer = (
            analyzer
            if analyzer is not None
            else MultiTimeframeAnalyzer()
        )

    @staticmethod
    def _analyze_candles(
        candles: list[dict],
    ) -> dict:

        if not candles:
            return {
                "trend": "NEUTRAL",
                "momentum": "NEUTRAL",
                "data_available": False,
                "data_quality": "MISSING",
            }

        if len(candles) < 50:
            return {
                "trend": "NEUTRAL",
                "momentum": "NEUTRAL",
                "data_available": True,
                "data_quality": "POOR",
            }

        closes = [
            float(candle["close"])
            for candle in candles
        ]

        sma20 = calculate_sma(
            closes,
            period=20,
        )

        sma50 = calculate_sma(
            closes,
            period=50,
        )

        rsi_values = calculate_rsi(
            closes,
            period=14,
        )

        latest = closes[-1]
        latest_sma20 = sma20[-1]
        latest_sma50 = sma50[-1]
        latest_rsi = rsi_values[-1]

        if (
            latest_sma20 is None
            or latest_sma50 is None
        ):
            return {
                "trend": "NEUTRAL",
                "momentum": "NEUTRAL",
                "data_available": True,
                "data_quality": "POOR",
            }

        if latest_sma20 > latest_sma50:
            trend = "BULLISH"
        elif latest_sma20 < latest_sma50:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"

        if (
            latest > latest_sma20
            and latest_rsi >= 55
        ):
            momentum = "POSITIVE"

        elif (
            latest < latest_sma20
            and latest_rsi <= 45
        ):
            momentum = "NEGATIVE"

        else:
            momentum = "NEUTRAL"

        return {
            "trend": trend,
            "momentum": momentum,
            "data_available": True,
            "data_quality": "GOOD",
        }

    def analyze(
        self,
        symbol: str,
    ) -> MultiTimeframeAnalysis:

        timeframe_data = {}

        for timeframe, config in (
            self.CONFIG.items()
        ):

            candles = self.market_data.get(
                symbol,
                period=config["period"],
                interval=config["interval"],
            )

            timeframe_data[timeframe] = (
                self._analyze_candles(
                    candles
                )
            )

        return self.analyzer.analyze(
            symbol,
            timeframe_data,
        )
