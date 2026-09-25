"""
ATLAS Portfolio Service

Paper-trading portfolio calculations.
No live orders.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass
class Position:
    symbol: str
    quantity: float
    average_price_usd: float
    current_price_usd: float
    last_buy_price_usd: float | None = None
    peak_price_usd: float | None = None

    def __post_init__(self):
        if self.last_buy_price_usd is None:
            self.last_buy_price_usd = self.average_price_usd
        if self.peak_price_usd is None:
            self.peak_price_usd = self.current_price_usd

    @property
    def invested_usd(self):
        return self.quantity * self.average_price_usd

    @property
    def market_value_usd(self):
        return self.quantity * self.current_price_usd

    @property
    def pnl_usd(self):
        return self.market_value_usd - self.invested_usd

    @property
    def pnl_percent(self):
        return (
            self.pnl_usd / self.invested_usd * 100
            if self.invested_usd
            else 0.0
        )


@dataclass
class PortfolioSnapshot:
    starting_capital_nok: float
    cash_nok: float
    profit_vault_nok: float
    positions: List[Position] = field(default_factory=list)
    usd_nok: float = 1.0

    @property
    def positions_value_nok(self):
        return sum(
            p.market_value_usd
            for p in self.positions
        ) * self.usd_nok

    @property
    def invested_nok(self):
        return sum(
            p.invested_usd
            for p in self.positions
        ) * self.usd_nok

    @property
    def unrealized_pnl_nok(self):
        return sum(
            p.pnl_usd
            for p in self.positions
        ) * self.usd_nok

    @property
    def total_equity_nok(self):
        return (
            self.cash_nok
            + self.positions_value_nok
            + self.profit_vault_nok
        )

    @property
    def total_pnl_nok(self):
        return (
            self.total_equity_nok
            - self.starting_capital_nok
        )

    @property
    def return_percent(self):
        return (
            self.total_pnl_nok
            / self.starting_capital_nok
            * 100
            if self.starting_capital_nok
            else 0.0
        )


class PortfolioService:
    """
    Paper-trading portfolio.

    This service never places real orders.
    """

    def __init__(
        self,
        starting_capital_nok=5000.0,
    ):
        self.starting_capital_nok = (
            float(starting_capital_nok)
        )

        self._cash_nok = (
            self.starting_capital_nok
        )

        self._profit_vault_nok = 0.0

        self._positions: Dict[str, Position] = {}

    def restore_from_trades(self, trades):
        """Rebuild paper-account state from persisted trade history.

        ``TradingService`` remains the owner of trade history. This method
        only rehydrates PortfolioService state after a process restart; it
        does not persist trades or make trading decisions.
        """
        self.reset()

        def value(trade, key):
            if isinstance(trade, dict):
                return trade[key]
            return getattr(trade, key)

        def timestamp(trade):
            current = value(trade, "timestamp")
            if isinstance(current, str):
                return datetime.fromisoformat(current)
            return current

        ordered_trades = sorted(trades, key=timestamp)

        for trade in ordered_trades:
            symbol = str(value(trade, "symbol"))
            action = str(value(trade, "action"))
            quantity = float(value(trade, "quantity"))
            price_usd = float(value(trade, "price_usd"))
            amount_nok = float(value(trade, "amount_nok"))

            if action == "BUY":
                if quantity <= 0.0 or price_usd <= 0.0 or amount_nok <= 0.0:
                    raise ValueError("Invalid persisted BUY trade.")

                existing = self._positions.get(symbol)
                if existing is None:
                    self._positions[symbol] = Position(
                        symbol=symbol,
                        quantity=quantity,
                        average_price_usd=price_usd,
                        current_price_usd=price_usd,
                        last_buy_price_usd=price_usd,
                    )
                else:
                    total_quantity = existing.quantity + quantity
                    total_cost = existing.invested_usd + quantity * price_usd
                    existing.quantity = total_quantity
                    existing.average_price_usd = total_cost / total_quantity
                    existing.current_price_usd = price_usd
                    existing.last_buy_price_usd = price_usd

                self._cash_nok -= amount_nok
                continue

            if action == "SELL":
                if quantity <= 0.0 or price_usd <= 0.0 or amount_nok < 0.0:
                    raise ValueError("Invalid persisted SELL trade.")

                position = self._positions.get(symbol)
                if position is None:
                    raise ValueError(
                        f"Persisted SELL has no open position for {symbol}."
                    )
                if quantity > position.quantity + 1e-12:
                    raise ValueError(
                        f"Persisted SELL exceeds current position for {symbol}."
                    )

                realized_pnl_nok = float(value(trade, "realized_pnl_nok"))
                self._cash_nok += amount_nok
                if realized_pnl_nok > 0.0:
                    self._cash_nok -= realized_pnl_nok
                    self._profit_vault_nok += realized_pnl_nok

                remaining_quantity = position.quantity - quantity
                if remaining_quantity <= 1e-12:
                    del self._positions[symbol]
                else:
                    position.quantity = remaining_quantity
                    position.current_price_usd = price_usd
                continue

            raise ValueError(f"Unsupported persisted trade action: {action}")

    # -------------------------------------------------
    # PRICE UPDATE
    # -------------------------------------------------

    def update_prices(self, prices_usd):
        """
        Update current market prices for
        existing paper positions.
        """

        for symbol, position in (
            self._positions.items()
        ):

            if symbol in prices_usd:

                price_usd = float(prices_usd[symbol])
                position.current_price_usd = price_usd
                position.peak_price_usd = max(
                    position.peak_price_usd,
                    price_usd,
                )

    # -------------------------------------------------
    # BUY
    # -------------------------------------------------

    def buy(
        self,
        symbol,
        amount_nok,
        price_usd,
        usd_nok,
    ):
        """
        Buy a paper position using NOK.

        amount_nok = amount of cash to invest.
        """

        amount_nok = float(amount_nok)
        price_usd = float(price_usd)
        usd_nok = float(usd_nok)

        if amount_nok <= 0:
            raise ValueError(
                "Buy amount must be greater than zero."
            )

        if price_usd <= 0:
            raise ValueError(
                "Price must be greater than zero."
            )

        if usd_nok <= 0:
            raise ValueError(
                "USD/NOK rate must be greater than zero."
            )

        if amount_nok > self._cash_nok:
            raise ValueError(
                "Insufficient cash."
            )

        amount_usd = amount_nok / usd_nok

        quantity = amount_usd / price_usd

        existing = self._positions.get(symbol)

        if existing:

            total_quantity = (
                existing.quantity + quantity
            )

            total_cost = (
                existing.invested_usd
                + amount_usd
            )

            existing.quantity = total_quantity

            existing.average_price_usd = (
                total_cost / total_quantity
            )

            existing.current_price_usd = price_usd
            existing.last_buy_price_usd = price_usd

        else:

            self._positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                average_price_usd=price_usd,
                current_price_usd=price_usd,
                last_buy_price_usd=price_usd,
            )

        self._cash_nok -= amount_nok

        return self._positions[symbol]

    # -------------------------------------------------
    # SELL
    # -------------------------------------------------

    def sell(
        self,
        symbol,
        price_usd,
        usd_nok,
        quantity=None,
    ):
        """
        Sell a paper position.

        If quantity is omitted, the entire position
        is sold.

        Realized profit is moved into Profit Vault.
        """

        price_usd = float(price_usd)
        usd_nok = float(usd_nok)

        position = self._positions.get(symbol)

        if not position:
            raise ValueError(
                f"No open position for {symbol}."
            )

        if quantity is None:
            quantity = position.quantity
        else:
            quantity = float(quantity)

        if quantity <= 0:
            raise ValueError(
                "Sell quantity must be greater than zero."
            )

        if quantity > position.quantity:
            raise ValueError(
                "Cannot sell more than the current position."
            )

        sale_value_usd = (
            quantity * price_usd
        )

        sale_value_nok = (
            sale_value_usd * usd_nok
        )

        cost_usd = (
            quantity
            * position.average_price_usd
        )

        cost_nok = (
            cost_usd * usd_nok
        )

        realized_pnl_nok = (
            sale_value_nok - cost_nok
        )

        # The sale proceeds return to cash.
        self._cash_nok += sale_value_nok

        # Realized profit is separated into
        # the Profit Vault.
        if realized_pnl_nok > 0:

            self._cash_nok -= realized_pnl_nok

            self._profit_vault_nok += (
                realized_pnl_nok
            )

        remaining_quantity = (
            position.quantity - quantity
        )

        if remaining_quantity <= 1e-12:

            del self._positions[symbol]

        else:

            position.quantity = remaining_quantity

            position.current_price_usd = price_usd

        return {
            "symbol": symbol,
            "quantity": quantity,
            "sale_value_nok": round(
                sale_value_nok,
                2,
            ),
            "realized_pnl_nok": round(
                realized_pnl_nok,
                2,
            ),
        }

    # -------------------------------------------------
    # RESET
    # -------------------------------------------------

    def reset(self):
        """
        Reset the paper account to its
        original starting capital.
        """

        self._cash_nok = (
            self.starting_capital_nok
        )

        self._profit_vault_nok = 0.0

        self._positions.clear()

    # -------------------------------------------------
    # SNAPSHOT
    # -------------------------------------------------

    def as_dict(self, usd_nok):

        snapshot = PortfolioSnapshot(
            starting_capital_nok=(
                self.starting_capital_nok
            ),

            cash_nok=self._cash_nok,

            profit_vault_nok=(
                self._profit_vault_nok
            ),

            positions=list(
                self._positions.values()
            ),

            usd_nok=usd_nok,
        )

        positions = []

        for position in snapshot.positions:

            positions.append(
                {
                    "symbol": position.symbol,

                    "quantity": round(
                        position.quantity,
                        8,
                    ),

                    "average_price_usd": round(
                        position.average_price_usd,
                        2,
                    ),

                    "current_price_usd": round(
                        position.current_price_usd,
                        2,
                    ),

                    "peak_price_usd": round(
                        position.peak_price_usd,
                        2,
                    ),

                    "last_buy_price_usd": round(
                        position.last_buy_price_usd,
                        2,
                    ) if position.last_buy_price_usd is not None else None,

                    "invested_nok": round(
                        position.invested_usd
                        * usd_nok,
                        2,
                    ),

                    "market_value_nok": round(
                        position.market_value_usd
                        * usd_nok,
                        2,
                    ),

                    "pnl_nok": round(
                        position.pnl_usd
                        * usd_nok,
                        2,
                    ),

                    "pnl_percent": round(
                        position.pnl_percent,
                        2,
                    ),
                }
            )

        return {

            "starting_capital_nok": round(
                snapshot.starting_capital_nok,
                2,
            ),

            "cash_nok": round(
                snapshot.cash_nok,
                2,
            ),

            "profit_vault_nok": round(
                snapshot.profit_vault_nok,
                2,
            ),

            "invested_nok": round(
                snapshot.invested_nok,
                2,
            ),

            "positions_value_nok": round(
                snapshot.positions_value_nok,
                2,
            ),

            "unrealized_pnl_nok": round(
                snapshot.unrealized_pnl_nok,
                2,
            ),

            "total_equity_nok": round(
                snapshot.total_equity_nok,
                2,
            ),

            "total_pnl_nok": round(
                snapshot.total_pnl_nok,
                2,
            ),

            "return_percent": round(
                snapshot.return_percent,
                2,
            ),

            "position_count": len(
                snapshot.positions
            ),

            "positions": positions,
        }
