"""Build normalized descriptive derivatives-flow evidence for ATLAS.

This module combines already retrieved market observations.
It does not fetch market data or create trading actions or decisions.
"""

from __future__ import annotations

from atlas.trading.historical_derivatives_data import (
    DerivativesFlowObservation,
    OpenInterestObservation,
)


class DerivativesFlowBuilder:
    """Build descriptive spot/futures/open-interest flow observations."""

    @staticmethod
    def build(
        *,
        spot_kline: list,
        futures_kline: list,
        previous_open_interest: OpenInterestObservation,
        current_open_interest: OpenInterestObservation,
    ) -> DerivativesFlowObservation:
        if int(spot_kline[0]) != int(futures_kline[0]):
            raise ValueError("kline timestamps must match")

        spot_volume = float(spot_kline[5])
        futures_volume = float(futures_kline[5])

        if spot_volume <= 0 or futures_volume <= 0:
            raise ValueError("volume must be positive")

        spot_taker_buy_ratio = (
            float(spot_kline[9]) / spot_volume
        )
        futures_taker_buy_ratio = (
            float(futures_kline[9]) / futures_volume
        )

        previous_oi = previous_open_interest.open_interest
        current_oi = current_open_interest.open_interest

        if previous_oi <= 0:
            raise ValueError(
                "previous open interest must be positive"
            )

        open_interest_change = (
            current_oi - previous_oi
        ) / previous_oi

        return DerivativesFlowObservation(
            timestamp=float(spot_kline[0]) / 1000.0,
            spot_taker_buy_ratio=spot_taker_buy_ratio,
            futures_taker_buy_ratio=futures_taker_buy_ratio,
            open_interest_change=open_interest_change,
        )
