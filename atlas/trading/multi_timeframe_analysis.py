"""
Multi-timeframe day-trading analysis.

Combines directional information from multiple timeframes
using hierarchical timeframe weights.

This module does NOT place trades.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class TimeframeSignal:
    timeframe: str
    trend: str
    momentum: str
    signal: str
    confidence: float
    weight: float
    data_available: bool
    data_quality: str


@dataclass(slots=True)
class MultiTimeframeAnalysis:
    symbol: str
    timeframes: list[TimeframeSignal]
    overall_signal: str
    confidence: float
    alignment: float
    data_quality: str


class MultiTimeframeAnalyzer:
    """Combines independent timeframe signals."""

    TIMEFRAMES = (
        "4h",
        "1h",
        "15m",
        "5m",
        "1m",
    )

    WEIGHTS = {
        "4h": 0.35,
        "1h": 0.30,
        "15m": 0.20,
        "5m": 0.10,
        "1m": 0.05,
    }

    def analyze(
        self,
        symbol: str,
        timeframe_data: dict[str, dict],
    ) -> MultiTimeframeAnalysis:

        signals = []

        for timeframe in self.TIMEFRAMES:

            data = timeframe_data.get(timeframe)

            if not data:
                continue

            data_available = bool(
                data.get("data_available", True)
            )

            data_quality = str(
                data.get(
                    "data_quality",
                    "GOOD" if data_available else "MISSING",
                )
            ).upper()

            if not data_available:
                continue

            trend = str(
                data.get(
                    "trend",
                    "NEUTRAL",
                )
            ).upper()

            momentum = str(
                data.get(
                    "momentum",
                    "NEUTRAL",
                )
            ).upper()

            signal = self._signal(
                trend,
                momentum,
            )

            confidence = self._confidence(
                trend,
                momentum,
            )

            signals.append(
                TimeframeSignal(
                    timeframe=timeframe,
                    trend=trend,
                    momentum=momentum,
                    signal=signal,
                    confidence=confidence,
                    weight=self.WEIGHTS[timeframe],
                    data_available=True,
                    data_quality=data_quality,
                )
            )

        if not signals:
            return MultiTimeframeAnalysis(
                symbol=symbol,
                timeframes=[],
                overall_signal="WAIT",
                confidence=0.0,
                alignment=0.0,
                data_quality="MISSING",
            )

        weighted_buy = sum(
            item.weight
            for item in signals
            if item.signal == "BUY"
        )

        weighted_sell = sum(
            item.weight
            for item in signals
            if item.signal == "SELL"
        )

        weighted_wait = sum(
            item.weight
            for item in signals
            if item.signal == "WAIT"
        )

        total_weight = sum(
            item.weight
            for item in signals
        )

        if total_weight <= 0:
            return MultiTimeframeAnalysis(
                symbol=symbol,
                timeframes=signals,
                overall_signal="WAIT",
                confidence=0.0,
                alignment=0.0,
                data_quality="UNKNOWN",
            )

        normalized_buy = weighted_buy / total_weight
        normalized_sell = weighted_sell / total_weight
        normalized_wait = weighted_wait / total_weight

        primary_buy_confirmation = all(
            any(
                item.timeframe == timeframe
                and item.signal == "BUY"
                for item in signals
            )
            for timeframe in ("4h", "1h", "15m")
        )

        primary_sell_confirmation = all(
            any(
                item.timeframe == timeframe
                and item.signal == "SELL"
                for item in signals
            )
            for timeframe in ("4h", "1h", "15m")
        )

        enough_timeframes = len(signals) >= 3

        if (
            normalized_buy >= 0.60
            and weighted_buy > weighted_sell
            and primary_buy_confirmation
            and enough_timeframes
        ):
            overall_signal = "BUY"

        elif (
            normalized_sell >= 0.60
            and weighted_sell > weighted_buy
            and primary_sell_confirmation
            and enough_timeframes
        ):
            overall_signal = "SELL"

        else:
            overall_signal = "WAIT"

        alignment = (
            max(
                normalized_buy,
                normalized_sell,
                normalized_wait,
            )
            * 100
        )

        if overall_signal == "BUY":
            relevant = [
                item
                for item in signals
                if item.signal == "BUY"
            ]

        elif overall_signal == "SELL":
            relevant = [
                item
                for item in signals
                if item.signal == "SELL"
            ]

        else:
            relevant = signals

        confidence = (
            sum(
                item.confidence * item.weight
                for item in relevant
            )
            / sum(
                item.weight
                for item in relevant
            )
            if relevant
            else 0.0
        )

        data_quality = self._overall_data_quality(
            signals
        )

        return MultiTimeframeAnalysis(
            symbol=symbol,
            timeframes=signals,
            overall_signal=overall_signal,
            confidence=round(
                confidence,
                2,
            ),
            alignment=round(
                alignment,
                2,
            ),
            data_quality=data_quality,
        )

    @staticmethod
    def _overall_data_quality(
        signals: list[TimeframeSignal],
    ) -> str:

        qualities = {
            signal.data_quality
            for signal in signals
        }

        if "POOR" in qualities:
            return "POOR"

        if "PARTIAL" in qualities:
            return "PARTIAL"

        if "MISSING" in qualities:
            return "PARTIAL"

        return "GOOD"

    @staticmethod
    def _signal(
        trend: str,
        momentum: str,
    ) -> str:

        if (
            trend == "BULLISH"
            and momentum == "POSITIVE"
        ):
            return "BUY"

        if (
            trend == "BEARISH"
            and momentum == "NEGATIVE"
        ):
            return "SELL"

        return "WAIT"

    @staticmethod
    def _confidence(
        trend: str,
        momentum: str,
    ) -> float:

        if (
            trend == "BULLISH"
            and momentum == "POSITIVE"
        ):
            return 90.0

        if (
            trend == "BEARISH"
            and momentum == "NEGATIVE"
        ):
            return 90.0

        if trend in {
            "BULLISH",
            "BEARISH",
        }:
            return 65.0

        return 45.0
