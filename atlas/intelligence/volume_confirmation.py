"""
Volume Confirmation

Determines how market volume confirms or weakens
an existing BUY / SELL / HOLD technical signal.

Volume never creates the trading direction.
It only evaluates confirmation strength.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class VolumeConfirmation:
    """Structured interpretation of volume confirmation."""

    action: str
    volume_level: str
    volume_ratio: float
    strength: str
    interpretation: str


def confirm_volume(
    action: str,
    volume_level: str,
    volume_ratio: float,
) -> VolumeConfirmation:
    """
    Evaluate how volume confirms an existing market direction.

    Rules:

    BUY/SELL:
        EXTREME -> VERY_STRONG
        STRONG  -> STRONG
        NORMAL  -> NORMAL
        LOW     -> WEAK

    HOLD:
        EXTREME -> HIGH_ACTIVITY
        STRONG  -> HIGH_ACTIVITY
        NORMAL  -> NORMAL
        LOW     -> LOW_ACTIVITY

    UNKNOWN volume always produces UNKNOWN confirmation.
    """

    action = str(action).upper()
    volume_level = str(volume_level).upper()
    volume_ratio = float(volume_ratio)

    if volume_level == "UNKNOWN":

        return VolumeConfirmation(
            action=action,
            volume_level=volume_level,
            volume_ratio=volume_ratio,
            strength="UNKNOWN",
            interpretation=(
                "Volume confirmation is unavailable."
            ),
        )

    if action in {"BUY", "SELL"}:

        if volume_level == "EXTREME":

            strength = "VERY_STRONG"
            interpretation = (
                f"{action} signal has very strong volume "
                f"confirmation at {volume_ratio:.2f}x average volume."
            )

        elif volume_level == "STRONG":

            strength = "STRONG"
            interpretation = (
                f"{action} signal has strong volume "
                f"confirmation at {volume_ratio:.2f}x average volume."
            )

        elif volume_level == "NORMAL":

            strength = "NORMAL"
            interpretation = (
                f"{action} signal has normal volume "
                f"confirmation at {volume_ratio:.2f}x average volume."
            )

        else:

            strength = "WEAK"
            interpretation = (
                f"{action} signal has weak volume "
                f"confirmation at {volume_ratio:.2f}x average volume."
            )

    elif action == "HOLD":

        if volume_level in {"EXTREME", "STRONG"}:

            strength = "HIGH_ACTIVITY"
            interpretation = (
                f"HOLD with elevated market activity at "
                f"{volume_ratio:.2f}x average volume; "
                "direction remains unclear."
            )

        elif volume_level == "NORMAL":

            strength = "NORMAL"
            interpretation = (
                f"HOLD with normal market activity at "
                f"{volume_ratio:.2f}x average volume."
            )

        else:

            strength = "LOW_ACTIVITY"
            interpretation = (
                f"HOLD with low market activity at "
                f"{volume_ratio:.2f}x average volume."
            )

    else:

        strength = "UNKNOWN"
        interpretation = (
            f"Volume confirmation is unavailable for "
            f"action {action}."
        )

    return VolumeConfirmation(
        action=action,
        volume_level=volume_level,
        volume_ratio=volume_ratio,
        strength=strength,
        interpretation=interpretation,
    )
