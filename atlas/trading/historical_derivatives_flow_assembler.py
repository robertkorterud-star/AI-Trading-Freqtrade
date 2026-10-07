"""Assemble historical derivatives-flow observations from aligned market data.

This module aligns already retrieved historical spot/futures klines and open
interest observations. It does not fetch data or create trading decisions.
"""

from __future__ import annotations

from atlas.trading.derivatives_flow_builder import DerivativesFlowBuilder
from atlas.trading.historical_derivatives_data import (
    DerivativesFlowObservation,
    OpenInterestObservation,
)


class HistoricalDerivativesFlowAssembler:
    """Align completed klines with their boundary open-interest observations."""

    def assemble(
        self,
        *,
        spot_klines: tuple[list, ...],
        futures_klines: tuple[list, ...],
        open_interest: tuple[OpenInterestObservation, ...],
    ) -> tuple[DerivativesFlowObservation, ...]:
        futures_by_open_time = {
            int(kline[0]): kline
            for kline in futures_klines
        }
        oi_by_time = {
            int(observation.timestamp.timestamp() * 1000): observation
            for observation in open_interest
        }

        observations = []

        for spot_kline in spot_klines:
            open_time = int(spot_kline[0])
            close_boundary = int(spot_kline[6]) + 1

            futures_kline = futures_by_open_time.get(open_time)
            previous_oi = oi_by_time.get(open_time)
            current_oi = oi_by_time.get(close_boundary)

            if (
                futures_kline is None
                or previous_oi is None
                or current_oi is None
            ):
                continue

            observations.append(
                DerivativesFlowBuilder.build(
                    spot_kline=spot_kline,
                    futures_kline=futures_kline,
                    previous_open_interest=previous_oi,
                    current_open_interest=current_oi,
                )
            )

        return tuple(observations)
