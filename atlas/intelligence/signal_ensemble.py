"""Signal ensemble for combining independent ATLAS signal engines."""

from dataclasses import dataclass
from typing import Iterable

from atlas.models.action import Action


@dataclass(frozen=True)
class EnsembleSignal:
    """Combined directional signal produced by the ATLAS signal ensemble."""

    action: Action
    confidence: float
    contributors: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class SignalInput:
    """Normalized input from one independent signal algorithm."""

    name: str
    action: Action
    confidence: float
    reasons: tuple[str, ...] = ()


class SignalEnsemble:
    """Combines independent signals without executing trades."""

    def combine(self, signals: Iterable[SignalInput]) -> EnsembleSignal:
        signals = tuple(signals)
        if not signals:
            raise ValueError("No signals provided.")

        for signal in signals:
            if not 0.0 <= signal.confidence <= 100.0:
                raise ValueError("Signal confidence must be between 0 and 100.")

        scores = {action: 0.0 for action in Action}
        for signal in signals:
            scores[signal.action] += signal.confidence

        action, dominant_score = max(scores.items(), key=lambda item: item[1])
        total_score = sum(scores.values())
        confidence = dominant_score / total_score * 100.0 if total_score else 0.0

        return EnsembleSignal(
            action=action,
            confidence=confidence,
            contributors=tuple(signal.name for signal in signals),
            reasons=tuple(
                f"{signal.name}: {signal.action.value} ({signal.confidence:.1f}/100)."
                for signal in signals
            ),
        )
