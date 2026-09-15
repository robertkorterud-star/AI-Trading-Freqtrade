"""Continuous ATLAS runtime loop.

The loop owns scheduling only. Decision-making remains in AtlasEngine.
"""

import time

from atlas.core.config import AtlasConfig
from atlas.core.engine import AtlasEngine
from atlas.market.candidates.research_scheduler import CandidateResearchScheduler
from atlas.market.trigger import MarketState, MarketStateTrigger


class AtlasRuntimeLoop:
    """Run the canonical AtlasEngine cycle when runtime triggers warrant it."""

    def __init__(
        self,
        engine: AtlasEngine | None = None,
        interval_seconds: float = 30.0,
        research_scheduler: CandidateResearchScheduler | None = None,
    ):
        self.engine = engine or AtlasEngine()
        self.interval_seconds = float(interval_seconds)
        if self.interval_seconds <= 0.0:
            raise ValueError("interval_seconds must be greater than zero")

        self.research_scheduler = (
            research_scheduler
            or CandidateResearchScheduler(
                service=self.engine.candidate_research_service,
            )
        )
        self._market_state_triggers: dict[str, MarketStateTrigger] = {}

    def _get_trigger(self, symbol: str) -> MarketStateTrigger:
        """Return the stable per-symbol trigger used by the runtime."""

        trigger = self._market_state_triggers.get(symbol)
        if trigger is None:
            trigger = MarketStateTrigger(
                min_trigger_interval_seconds=self.interval_seconds,
            )
            self._market_state_triggers[symbol] = trigger
        return trigger

    def _get_market_states(self) -> list[MarketState]:
        """Build lightweight trigger states from the engine's existing market service."""

        states: list[MarketState] = []
        for asset in self.engine.asset_universe.all():
            try:
                snapshot = self.engine.technical.get_snapshot(asset.symbol)
            except Exception:
                continue

            states.append(
                MarketState(
                    symbol=snapshot.symbol,
                    price=snapshot.price,
                    previous_close=snapshot.previous_close,
                    change_percent=snapshot.change_percent,
                    trend=snapshot.trend,
                    volume_ratio=snapshot.volume_ratio,
                )
            )

        return states

    def run_once(self) -> bool:
        """Run scheduled maintenance and trigger one canonical engine cycle if needed."""

        if self.research_scheduler.should_research():
            context = self.research_scheduler.research()
            if context is not None:
                self.engine.logger.info(
                    "ATLAS candidate research context refreshed."
                )

        for state in self._get_market_states():
            if self._get_trigger(state.symbol).should_analyze(state):
                self.engine.start()
                return True

        return False

    def run_forever(self):
        """Run the runtime scheduler continuously until interrupted."""
        while True:
            started_at = time.monotonic()
            self.run_once()
            elapsed = time.monotonic() - started_at
            time.sleep(max(0.0, self.interval_seconds - elapsed))


def run(config: AtlasConfig | None = None, interval_seconds: float = 30.0):
    """Start the continuous canonical ATLAS runtime."""
    AtlasRuntimeLoop(
        engine=AtlasEngine(config=config),
        interval_seconds=interval_seconds,
    ).run_forever()
