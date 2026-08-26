"""
ATLAS Historical Market Data Quality.

Validates normalized historical OHLCV data before research.

This module does not create trading decisions.
"""

from dataclasses import dataclass
from datetime import timedelta

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
)


@dataclass(frozen=True, slots=True)
class HistoricalDataQualityResult:
    valid: bool

    bar_count: int
    duplicate_count: int
    invalid_ohlc_count: int
    non_positive_price_count: int

    expected_interval_seconds: float | None
    gap_count: int
    largest_gap_seconds: float

    coverage_ratio_percent: float

    issues: tuple[str, ...]


class HistoricalDataQualityValidator:
    """Checks structural quality of historical market data."""

    def validate(
        self,
        data: HistoricalMarketData,
    ) -> HistoricalDataQualityResult:

        bars = list(data.bars)

        if not bars:
            return HistoricalDataQualityResult(
                valid=False,
                bar_count=0,
                duplicate_count=0,
                invalid_ohlc_count=0,
                non_positive_price_count=0,
                expected_interval_seconds=None,
                gap_count=0,
                largest_gap_seconds=0.0,
                coverage_ratio_percent=0.0,
                issues=("Dataset is empty.",),
            )

        duplicate_count = 0
        invalid_ohlc_count = 0
        non_positive_price_count = 0
        issues: list[str] = []

        timestamps = [
            bar.timestamp
            for bar in bars
        ]

        for index in range(1, len(timestamps)):
            if timestamps[index] == timestamps[index - 1]:
                duplicate_count += 1

        for bar in bars:

            prices = (
                bar.open,
                bar.high,
                bar.low,
                bar.close,
            )

            if any(
                price <= 0
                for price in prices
            ):
                non_positive_price_count += 1

            if (
                bar.high
                < max(bar.open, bar.close)
                or
                bar.low
                > min(bar.open, bar.close)
            ):
                invalid_ohlc_count += 1

        intervals = []

        for index in range(1, len(timestamps)):

            seconds = (
                timestamps[index]
                - timestamps[index - 1]
            ).total_seconds()

            if seconds > 0:
                intervals.append(seconds)

        expected_interval_seconds = (
            self._expected_interval(
                intervals
            )
        )

        gap_count = 0
        largest_gap_seconds = 0.0

        if expected_interval_seconds:

            for seconds in intervals:

                if seconds > (
                    expected_interval_seconds * 1.5
                ):
                    gap_count += 1
                    largest_gap_seconds = max(
                        largest_gap_seconds,
                        seconds,
                    )

        if duplicate_count:
            issues.append(
                f"Found {duplicate_count} duplicate timestamps."
            )

        if invalid_ohlc_count:
            issues.append(
                f"Found {invalid_ohlc_count} invalid OHLC bars."
            )

        if non_positive_price_count:
            issues.append(
                "Found "
                f"{non_positive_price_count} bars "
                "with non-positive prices."
            )

        if gap_count:
            issues.append(
                f"Found {gap_count} data gaps."
            )

        valid = (
            duplicate_count == 0
            and invalid_ohlc_count == 0
            and non_positive_price_count == 0
        )

        coverage_ratio_percent = (
            self._coverage_ratio(
                intervals=intervals,
                expected_interval_seconds=(
                    expected_interval_seconds
                ),
            )
        )

        return HistoricalDataQualityResult(
            valid=valid,
            bar_count=len(bars),
            duplicate_count=duplicate_count,
            invalid_ohlc_count=invalid_ohlc_count,
            non_positive_price_count=(
                non_positive_price_count
            ),
            expected_interval_seconds=(
                expected_interval_seconds
            ),
            gap_count=gap_count,
            largest_gap_seconds=(
                largest_gap_seconds
            ),
            coverage_ratio_percent=(
                coverage_ratio_percent
            ),
            issues=tuple(issues),
        )

    @staticmethod
    def _expected_interval(
        intervals: list[float],
    ) -> float | None:

        if not intervals:
            return None

        ordered = sorted(intervals)

        middle = len(ordered) // 2

        if len(ordered) % 2:
            return ordered[middle]

        return (
            ordered[middle - 1]
            + ordered[middle]
        ) / 2.0

    @staticmethod
    def _coverage_ratio(
        *,
        intervals: list[float],
        expected_interval_seconds: float | None,
    ) -> float:

        if (
            not intervals
            or expected_interval_seconds is None
            or expected_interval_seconds <= 0
        ):
            return 100.0

        expected_total = (
            len(intervals)
            * expected_interval_seconds
        )

        actual_total = sum(intervals)

        if actual_total <= 0:
            return 0.0

        missing = max(
            actual_total - expected_total,
            0.0,
        )

        return max(
            0.0,
            (
                1.0
                - missing / actual_total
            )
            * 100.0,
        )
