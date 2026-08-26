"""
ATLAS Crypto Market Breadth.

Measures participation across a crypto market universe.

This module does not generate trading decisions.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class CryptoMarketBreadth:
    total_assets: int
    advancing_assets: int
    declining_assets: int
    unchanged_assets: int

    advance_ratio: float
    decline_ratio: float

    average_change_24h: float | None
    median_change_24h: float | None

    volume_up_assets: int
    volume_down_assets: int

    breadth_regime: str
    data_quality: str


class CryptoMarketBreadthAnalyzer:
    """Analyze participation across crypto assets."""

    def analyze(
        self,
        assets: list,
    ) -> CryptoMarketBreadth:

        if not assets:
            return CryptoMarketBreadth(
                total_assets=0,
                advancing_assets=0,
                declining_assets=0,
                unchanged_assets=0,
                advance_ratio=0.0,
                decline_ratio=0.0,
                average_change_24h=None,
                median_change_24h=None,
                volume_up_assets=0,
                volume_down_assets=0,
                breadth_regime="UNKNOWN",
                data_quality="MISSING",
            )

        changes = [
            asset.change_24h
            for asset in assets
            if asset.change_24h is not None
        ]

        advancing = sum(
            1
            for asset in assets
            if asset.change_24h is not None
            and asset.change_24h > 0
        )

        declining = sum(
            1
            for asset in assets
            if asset.change_24h is not None
            and asset.change_24h < 0
        )

        unchanged = sum(
            1
            for asset in assets
            if asset.change_24h is not None
            and asset.change_24h == 0
        )

        total = len(assets)

        advance_ratio = (
            advancing / total
            if total
            else 0.0
        )

        decline_ratio = (
            declining / total
            if total
            else 0.0
        )

        average_change = (
            sum(changes) / len(changes)
            if changes
            else None
        )

        median_change = (
            self._median(changes)
            if changes
            else None
        )

        volume_up = sum(
            1
            for asset in assets
            if (
                asset.volume_24h is not None
                and asset.change_24h is not None
                and asset.change_24h > 0
                and asset.volume_24h > 0
            )
        )

        volume_down = sum(
            1
            for asset in assets
            if (
                asset.volume_24h is not None
                and asset.change_24h is not None
                and asset.change_24h < 0
                and asset.volume_24h > 0
            )
        )

        regime = self._regime(
            advance_ratio=advance_ratio,
            decline_ratio=decline_ratio,
            average_change=average_change,
        )

        quality = self._quality(
            total=total,
            valid_changes=len(changes),
        )

        return CryptoMarketBreadth(
            total_assets=total,
            advancing_assets=advancing,
            declining_assets=declining,
            unchanged_assets=unchanged,
            advance_ratio=round(
                advance_ratio,
                4,
            ),
            decline_ratio=round(
                decline_ratio,
                4,
            ),
            average_change_24h=(
                round(
                    average_change,
                    4,
                )
                if average_change is not None
                else None
            ),
            median_change_24h=(
                round(
                    median_change,
                    4,
                )
                if median_change is not None
                else None
            ),
            volume_up_assets=volume_up,
            volume_down_assets=volume_down,
            breadth_regime=regime,
            data_quality=quality,
        )

    @staticmethod
    def _regime(
        advance_ratio: float,
        decline_ratio: float,
        average_change: float | None,
    ) -> str:

        if average_change is None:
            return "UNKNOWN"

        if (
            advance_ratio >= 0.65
            and average_change > 0
        ):
            return "BROAD_BULLISH"

        if (
            decline_ratio >= 0.65
            and average_change < 0
        ):
            return "BROAD_BEARISH"

        if (
            advance_ratio >= 0.55
            and average_change > 0
        ):
            return "BULLISH_PARTICIPATION"

        if (
            decline_ratio >= 0.55
            and average_change < 0
        ):
            return "BEARISH_PARTICIPATION"

        return "MIXED"

    @staticmethod
    def _quality(
        total: int,
        valid_changes: int,
    ) -> str:

        if total == 0:
            return "MISSING"

        if valid_changes == 0:
            return "POOR"

        coverage = valid_changes / total

        if coverage < 0.5:
            return "POOR"

        if coverage < 0.9:
            return "PARTIAL"

        return "GOOD"

    @staticmethod
    def _median(
        values: list[float],
    ) -> float:

        ordered = sorted(values)
        middle = len(ordered) // 2

        if len(ordered) % 2:
            return ordered[middle]

        return (
            ordered[middle - 1]
            + ordered[middle]
        ) / 2
