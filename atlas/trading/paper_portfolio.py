"""
ATLAS Paper Portfolio

Virtual portfolio used by the dry-run trading engine.

No real orders are submitted.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PaperPosition:
    """Virtual long position."""

    symbol: str
    quantity: float
    average_price: float
    peak_price: float | None = None


@dataclass
class PaperPortfolio:
    """
    Virtual trading account.

    The portfolio intentionally models cash, positions and realized P&L
    without connecting to an exchange.
    """

    initial_cash: float = 100_000.0
    fee_rate: float = 0.001
    cash: float | None = None
    positions: dict[str, PaperPosition] = field(default_factory=dict)
    realized_pnl: float = 0.0

    def __post_init__(self) -> None:
        if self.initial_cash <= 0.0:
            raise ValueError("initial_cash must be greater than zero")

        if not 0.0 <= self.fee_rate < 1.0:
            raise ValueError("fee_rate must be between 0 and 1")

        if self.cash is None:
            self.cash = self.initial_cash

    def buy(self, symbol: str, price: float, quantity: float) -> PaperPosition:
        """Buy a virtual long position."""

        self._validate_trade(price, quantity)

        gross = price * quantity
        fee = gross * self.fee_rate
        total = gross + fee

        if total > self.cash:
            raise ValueError("insufficient paper cash")

        self.cash -= total

        existing = self.positions.get(symbol)

        if existing is None:
            position = PaperPosition(
                symbol=symbol,
                quantity=quantity,
                average_price=price,
                peak_price=price,
            )
        else:
            new_quantity = existing.quantity + quantity
            average_price = (
                existing.quantity * existing.average_price
                + quantity * price
            ) / new_quantity

            position = PaperPosition(
                symbol=symbol,
                quantity=new_quantity,
                average_price=average_price,
                peak_price=max(
                    existing.peak_price
                    if existing.peak_price is not None
                    else existing.average_price,
                    price,
                ),
            )

        self.positions[symbol] = position

        return position

    def sell(self, symbol: str, price: float, quantity: float) -> float:
        """Sell a virtual long position and return realized P&L."""

        self._validate_trade(price, quantity)

        position = self.positions.get(symbol)

        if position is None:
            raise ValueError("no paper position exists")

        if quantity > position.quantity:
            raise ValueError("cannot sell more than current position")

        gross = price * quantity
        fee = gross * self.fee_rate
        proceeds = gross - fee

        cost_basis = position.average_price * quantity
        pnl = proceeds - cost_basis

        self.cash += proceeds
        self.realized_pnl += pnl

        remaining = position.quantity - quantity

        if remaining <= 1e-12:
            del self.positions[symbol]
        else:
            self.positions[symbol] = PaperPosition(
                symbol=symbol,
                quantity=remaining,
                average_price=position.average_price,
                peak_price=position.peak_price,
            )

        return pnl

    def observe_price(self, symbol: str, price: float) -> PaperPosition | None:
        """Record the highest observed price for an open paper position."""

        if price <= 0.0:
            raise ValueError("price must be greater than zero")

        position = self.positions.get(symbol)

        if position is None:
            return None

        peak_price = max(
            position.peak_price
            if position.peak_price is not None
            else position.average_price,
            price,
        )

        if peak_price == position.peak_price:
            return position

        updated = PaperPosition(
            symbol=position.symbol,
            quantity=position.quantity,
            average_price=position.average_price,
            peak_price=peak_price,
        )
        self.positions[symbol] = updated
        return updated

    def equity(self, prices: dict[str, float]) -> float:
        """Return total marked-to-market paper equity."""

        value = self.cash

        for symbol, position in self.positions.items():
            price = prices.get(symbol, position.average_price)
            value += position.quantity * price

        return value

    def unrealized_pnl(self, prices: dict[str, float]) -> float:
        """Return unrealized P&L across open positions."""

        total = 0.0

        for symbol, position in self.positions.items():
            price = prices.get(symbol, position.average_price)
            total += (price - position.average_price) * position.quantity

        return total

    def position_value(
        self,
        symbol: str,
        price: float,
    ) -> float:
        """Return current marked value of a position."""

        position = self.positions.get(symbol)

        if position is None:
            return 0.0

        return position.quantity * price

    @staticmethod
    def _validate_trade(price: float, quantity: float) -> None:
        if price <= 0.0:
            raise ValueError("price must be greater than zero")

        if quantity <= 0.0:
            raise ValueError("quantity must be greater than zero")
