"""Research US opening-range expansion against future returns.

This module is research-only. It measures historical opening-range
behaviour and never creates trading actions or decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from atlas.trading.historical_market_data import HistoricalMarketData


_NEW_YORK = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class OpeningRangeResearchObservation:
    available_at: datetime
    opening_range_percent: float
    reference_range_percent: float
    range_expansion_ratio: float
    forward_return_percent: float


@dataclass(frozen=True, slots=True)
class OpeningRangeResearchResult:
    symbol: str
    timeframe: str
    source: str
    observations: tuple[OpeningRangeResearchObservation, ...]


class OpeningRangeResearch:
    """Measure US opening-range expansion without creating trades."""

    def __init__(
        self,
        *,
        opening_minutes: int = 15,
        reference_minutes: int = 15,
        forward_period: int = 1,
    ):
        if opening_minutes <= 0:
            raise ValueError("opening_minutes must be positive")
        if reference_minutes <= 0:
            raise ValueError("reference_minutes must be positive")
        if forward_period <= 0:
            raise ValueError("forward_period must be positive")

        self.opening_minutes = int(opening_minutes)
        self.reference_minutes = int(reference_minutes)
        self.forward_period = int(forward_period)

    def run(
        self,
        data: HistoricalMarketData,
    ) -> OpeningRangeResearchResult:
        bars = data.bars
        observations = []

        for opening_start_index, bar in enumerate(bars):
            timestamp = bar.timestamp

            if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                continue

            new_york_time = timestamp.astimezone(_NEW_YORK)

            if new_york_time.time().replace(tzinfo=None) != time(9, 30):
                continue

            cadence = self._cadence(bars, opening_start_index)

            if cadence is None:
                continue

            opening_duration = timedelta(minutes=self.opening_minutes)
            reference_duration = timedelta(minutes=self.reference_minutes)

            if (
                opening_duration % cadence != timedelta(0)
                or reference_duration % cadence != timedelta(0)
            ):
                continue

            opening_count = opening_duration // cadence
            reference_count = reference_duration // cadence

            opening_end_index = opening_start_index + opening_count
            reference_start_index = opening_start_index - reference_count

            if reference_start_index < 0:
                continue

            if opening_end_index > len(bars):
                continue

            reference_bars = bars[
                reference_start_index:opening_start_index
            ]
            opening_bars = bars[
                opening_start_index:opening_end_index
            ]

            if (
                len(reference_bars) != reference_count
                or len(opening_bars) != opening_count
            ):
                continue

            if not self._is_contiguous(
                reference_bars + opening_bars,
                cadence,
            ):
                continue

            forward_index = (
                opening_end_index - 1 + self.forward_period
            )

            if forward_index >= len(bars):
                continue

            opening_high = max(item.high for item in opening_bars)
            opening_low = min(item.low for item in opening_bars)
            opening_range = opening_high - opening_low

            reference_high = max(item.high for item in reference_bars)
            reference_low = min(item.low for item in reference_bars)
            reference_range = reference_high - reference_low

            if reference_range <= 0:
                continue

            opening_range_percent = (
                opening_range / opening_bars[0].open
            ) * 100.0

            reference_range_percent = (
                reference_range / reference_bars[0].open
            ) * 100.0

            current_close = opening_bars[-1].close
            future_close = bars[forward_index].close

            forward_return_percent = (
                (future_close / current_close) - 1.0
            ) * 100.0

            observations.append(
                OpeningRangeResearchObservation(
                    available_at=(
                        opening_bars[-1].timestamp + cadence
                    ),
                    opening_range_percent=opening_range_percent,
                    reference_range_percent=reference_range_percent,
                    range_expansion_ratio=(
                        opening_range / reference_range
                    ),
                    forward_return_percent=forward_return_percent,
                )
            )

        return OpeningRangeResearchResult(
            symbol=data.symbol,
            timeframe=data.timeframe,
            source=data.source,
            observations=tuple(observations),
        )

    @staticmethod
    def _cadence(bars, index):
        if index + 1 < len(bars):
            cadence = (
                bars[index + 1].timestamp
                - bars[index].timestamp
            )
        elif index > 0:
            cadence = (
                bars[index].timestamp
                - bars[index - 1].timestamp
            )
        else:
            return None

        if cadence <= timedelta(0):
            return None

        return cadence

    @staticmethod
    def _is_contiguous(bars, cadence):
        return all(
            current.timestamp - previous.timestamp == cadence
            for previous, current in zip(bars, bars[1:])
        )
