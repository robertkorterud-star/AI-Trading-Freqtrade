"""
ATLAS Trading Cost Model.

Estimates direct trading costs for paper-trading decisions.

This model intentionally covers only costs that belong to a trade:
fees, spread and slippage. Fixed operating/business costs are kept
outside the trading decision model.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TradingCostModel:
    """Estimate direct trading costs for a long round trip."""

    fee_rate: float = 0.001
    spread_bps: float = 2.0
    slippage_bps: float = 1.0

    def __post_init__(self) -> None:
        if self.fee_rate < 0.0:
            raise ValueError("fee_rate must be non-negative")
        if self.spread_bps < 0.0:
            raise ValueError("spread_bps must be non-negative")
        if self.slippage_bps < 0.0:
            raise ValueError("slippage_bps must be non-negative")

    @property
    def one_way_cost_rate(self) -> float:
        """Return estimated direct cost rate for one side of a trade."""
        spread_half_rate = self.spread_bps / 20_000.0
        slippage_rate = self.slippage_bps / 10_000.0
        return self.fee_rate + spread_half_rate + slippage_rate

    @property
    def round_trip_cost_rate(self) -> float:
        """Return estimated direct cost rate for entry plus exit."""
        return self.one_way_cost_rate * 2.0

    def one_way_cost(self, notional: float) -> float:
        """Return estimated direct cost amount for one trade side."""
        self._validate_notional(notional)
        return notional * self.one_way_cost_rate

    def round_trip_cost(self, notional: float) -> float:
        """Return estimated direct cost amount for a full round trip."""
        self._validate_notional(notional)
        return notional * self.round_trip_cost_rate

    def net_pnl(self, notional: float, gross_return: float) -> float:
        """Return expected net P&L after round-trip direct costs.

        ``gross_return`` is expressed as a decimal return, e.g. 0.01
        for +1%.
        """
        self._validate_notional(notional)
        return notional * (gross_return - self.round_trip_cost_rate)

    def net_return(self, gross_return: float) -> float:
        """Return expected decimal return after round-trip direct costs."""
        return gross_return - self.round_trip_cost_rate

    @staticmethod
    def _validate_notional(notional: float) -> None:
        if notional <= 0.0:
            raise ValueError("notional must be greater than zero")
