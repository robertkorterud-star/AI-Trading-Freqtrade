"""
Volume Intelligence

Interprets current market volume relative to average volume.

This module is explanatory only.
It does not make trading decisions.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class VolumeIntelligence:
    """
    Structured interpretation of market volume.
    """

    volume: float
    average_volume: float
    volume_ratio: float
    level: str
    interpretation: str


def analyze_volume(
    volume: float,
    average_volume: float,
    volume_ratio: float | None = None,
) -> VolumeIntelligence:
    """
    Analyze current volume relative to average volume.

    Classification:

    < 0.75x  -> LOW
    0.75-1.49x -> NORMAL
    1.50-2.99x -> STRONG
    >= 3.00x -> EXTREME

    Missing/invalid volume is classified as UNKNOWN.
    """

    volume = float(volume)
    average_volume = float(average_volume)

    if volume_ratio is None:

        if average_volume > 0:
            volume_ratio = volume / average_volume
        else:
            volume_ratio = 0.0

    volume_ratio = float(volume_ratio)

    if volume_ratio <= 0:

        return VolumeIntelligence(
            volume=volume,
            average_volume=average_volume,
            volume_ratio=volume_ratio,
            level="UNKNOWN",
            interpretation=(
                "Volume data is unavailable or insufficient "
                "for confirmation."
            ),
        )

    if volume_ratio < 0.75:

        level = "LOW"
        interpretation = (
            "Trading activity is below the recent average."
        )

    elif volume_ratio < 1.50:

        level = "NORMAL"
        interpretation = (
            "Trading activity is broadly in line "
            "with the recent average."
        )

    elif volume_ratio < 3.00:

        level = "STRONG"
        interpretation = (
            "Trading activity is significantly above "
            "the recent average."
        )

    else:

        level = "EXTREME"
        interpretation = (
            "Trading activity is exceptionally high "
            "relative to the recent average."
        )

    return VolumeIntelligence(
        volume=volume,
        average_volume=average_volume,
        volume_ratio=volume_ratio,
        level=level,
        interpretation=interpretation,
    )
