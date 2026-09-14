"""Cheap runtime trigger for deciding when full ATLAS analysis is worth it."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable


@dataclass(frozen=True, slots=True)
class MarketState:
    """Lightweight market snapshot used as a cheap change trigger."""

    symbol: str
    price: float
    previous_close: float
    change_percent: float
    trend: str
    volume_ratio: float

    @property
    def percent_move(self) -> float:
        return abs(float(self.change_percent))


class MarketStateTrigger:
    """Decide whether a market state change warrants a full analysis pass."""

    def __init__(
        self,
        *,
        min_change_percent: float = 1.0,
        min_volume_ratio_delta: float = 0.25,
        min_trigger_interval_seconds: float = 30.0,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.min_change_percent = float(min_change_percent)
        self.min_volume_ratio_delta = float(min_volume_ratio_delta)
        self.min_trigger_interval_seconds = float(min_trigger_interval_seconds)
        self._clock = clock or time.monotonic
        self._last_state: MarketState | None = None
        self._last_evaluation_at: float | None = None

    def _state_signature(self, state: MarketState) -> tuple:
        return (
            state.symbol,
            round(float(state.price), 4),
            round(float(state.previous_close), 4),
            round(float(state.change_percent), 4),
            state.trend,
            round(float(state.volume_ratio), 4),
        )

    def _materially_changed(
        self,
        state: MarketState,
        previous_state: MarketState,
    ) -> bool:
        if state.symbol != previous_state.symbol:
            return True

        if state.trend != previous_state.trend:
            return True

        if abs(float(state.change_percent) - float(previous_state.change_percent)) >= self.min_change_percent:
            return True

        if abs(float(state.volume_ratio) - float(previous_state.volume_ratio)) >= self.min_volume_ratio_delta:
            return True

        return False

    def should_analyze(self, state: MarketState | None) -> bool:
        """Return True only when a fresh state change merits a full analysis pass."""

        if state is None:
            return False

        now = self._clock()

        if self._last_state is None:
            self._last_state = state
            self._last_evaluation_at = now
            return True

        if self._state_signature(state) == self._state_signature(self._last_state):
            self._last_state = state
            self._last_evaluation_at = now
            return False

        changed = self._materially_changed(state, self._last_state)

        if not changed:
            self._last_state = state
            self._last_evaluation_at = now
            return False

        if (
            self._last_evaluation_at is not None
            and now - self._last_evaluation_at < self.min_trigger_interval_seconds
        ):
            self._last_evaluation_at = now
            return False

        self._last_state = state
        self._last_evaluation_at = now
        return True
