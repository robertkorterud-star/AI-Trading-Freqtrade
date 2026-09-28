"""
ATLAS Historical Market Data Quality.

Validates normalized historical OHLCV data before research.

This module does not create trading decisions.
"""

from dataclasses import dataclass
from datetime import datetime

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
    """Checks structural quality of historical market data.

    Gap detection is calendar-aware for equity-style daily (and weekly)
    series so ordinary weekends and short holiday closures are not
    reported as data defects.
    """

    # Gaps longer than this many expected bars are treated as abnormal
    # for continuous / intraday series.
    INTRADAY_GAP_MULTIPLIER = 1.5

    # For daily equity bars, allow normal weekend + short holiday pauses.
    # ~4 calendar days covers Fri close → Tue open around a Monday holiday.
    DAILY_NORMAL_GAP_SECONDS = 4.5 * 86400.0

    # Anything beyond a long holiday / data outage for daily bars.
    DAILY_ABNORMAL_GAP_SECONDS = 10.0 * 86400.0

    # Weekly bars: allow roughly two weeks between prints before flagging.
    WEEKLY_ABNORMAL_GAP_SECONDS = 16.0 * 86400.0

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

        expected_interval_seconds = self._expected_interval(intervals)
        session_style = self._session_style(
            timeframe=getattr(data, "timeframe", "unknown"),
            expected_interval_seconds=expected_interval_seconds,
        )

        gap_count = 0
        largest_gap_seconds = 0.0
        abnormal_intervals: list[float] = []

        for seconds in intervals:
            if self._is_abnormal_gap(
                seconds=seconds,
                expected_interval_seconds=expected_interval_seconds,
                session_style=session_style,
            ):
                gap_count += 1
                abnormal_intervals.append(seconds)
                largest_gap_seconds = max(largest_gap_seconds, seconds)

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
            if session_style in {"daily", "weekly"}:
                issues.append(
                    f"Found {gap_count} abnormal calendar gaps "
                    f"(beyond normal session closures)."
                )
            else:
                issues.append(
                    f"Found {gap_count} data gaps."
                )

        valid = (
            duplicate_count == 0
            and invalid_ohlc_count == 0
            and non_positive_price_count == 0
        )

        coverage_ratio_percent = self._coverage_ratio(
            intervals=intervals,
            expected_interval_seconds=expected_interval_seconds,
            session_style=session_style,
            abnormal_intervals=abnormal_intervals,
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

    @classmethod
    def _session_style(
        cls,
        *,
        timeframe: str,
        expected_interval_seconds: float | None,
    ) -> str:
        """Classify series as daily, weekly, or continuous/intraday."""

        normalized = (timeframe or "unknown").strip().lower()

        if normalized in {"1d", "1day", "day", "daily"}:
            return "daily"
        if normalized in {"1wk", "1w", "week", "weekly"}:
            return "weekly"

        if expected_interval_seconds is None:
            return "continuous"

        # Infer from observed median spacing when timeframe is unknown.
        if 20 * 3600 <= expected_interval_seconds <= 2.5 * 86400:
            return "daily"
        if 5 * 86400 <= expected_interval_seconds <= 10 * 86400:
            return "weekly"

        return "continuous"

    @classmethod
    def _is_abnormal_gap(
        cls,
        *,
        seconds: float,
        expected_interval_seconds: float | None,
        session_style: str,
    ) -> bool:
        """Return True only for gaps that look like missing data."""

        if session_style == "daily":
            # Weekends and short holidays are normal for equity dailies.
            return seconds > cls.DAILY_ABNORMAL_GAP_SECONDS

        if session_style == "weekly":
            return seconds > cls.WEEKLY_ABNORMAL_GAP_SECONDS

        if expected_interval_seconds is None or expected_interval_seconds <= 0:
            return False

        return seconds > (
            expected_interval_seconds * cls.INTRADAY_GAP_MULTIPLIER
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

    @classmethod
    def _coverage_ratio(
        cls,
        *,
        intervals: list[float],
        expected_interval_seconds: float | None,
        session_style: str,
        abnormal_intervals: list[float],
    ) -> float:
        """Estimate coverage while ignoring normal session closures."""

        if (
            not intervals
            or expected_interval_seconds is None
            or expected_interval_seconds <= 0
        ):
            return 100.0

        if session_style in {"daily", "weekly"}:
            # For session-based series, coverage is based only on abnormal
            # gaps rather than every weekend pause.
            if not abnormal_intervals:
                return 100.0

            span = sum(intervals)
            if span <= 0:
                return 0.0

            missing = sum(
                max(gap - expected_interval_seconds, 0.0)
                for gap in abnormal_intervals
            )
            return max(0.0, (1.0 - missing / span) * 100.0)

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
