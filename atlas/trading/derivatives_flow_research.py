"""Research derivatives-flow observations against future market returns.

This module is research-only. It measures historical relationships and does
not create trading actions or decisions.
"""

from __future__ import annotations

from dataclasses import dataclass

from atlas.trading.historical_derivatives_data import (
    DerivativesFlowObservation,
)
from atlas.trading.historical_market_data import HistoricalMarketData


@dataclass(frozen=True, slots=True)
class DerivativesFlowResearchObservation:
    """One derivatives-flow observation with its measured future return."""

    flow: DerivativesFlowObservation
    forward_return_percent: float


@dataclass(frozen=True, slots=True)
class DerivativesFlowResearchResult:
    """Historical derivatives-flow research result."""

    symbol: str
    timeframe: str
    source: str
    observations: tuple[DerivativesFlowResearchObservation, ...]


class DerivativesFlowResearch:
    """Measure derivatives-flow observations against later closes."""

    def __init__(self, forward_period: int = 1):
        if forward_period <= 0:
            raise ValueError("forward_period must be positive")

        self.forward_period = int(forward_period)

    def run(
        self,
        *,
        data: HistoricalMarketData,
        observations: tuple[DerivativesFlowObservation, ...],
    ) -> DerivativesFlowResearchResult:
        index_by_timestamp = {
            bar.timestamp.timestamp(): index
            for index, bar in enumerate(data.bars)
        }

        measured = []

        for flow in observations:
            index = index_by_timestamp.get(flow.timestamp)

            if index is None:
                continue

            forward_index = index + self.forward_period

            if forward_index >= len(data.bars):
                continue

            current_close = data.bars[index].close
            future_close = data.bars[forward_index].close

            forward_return_percent = (
                (future_close / current_close) - 1.0
            ) * 100.0

            measured.append(
                DerivativesFlowResearchObservation(
                    flow=flow,
                    forward_return_percent=forward_return_percent,
                )
            )

        return DerivativesFlowResearchResult(
            symbol=data.symbol,
            timeframe=data.timeframe,
            source=data.source,
            observations=tuple(measured),
        )
