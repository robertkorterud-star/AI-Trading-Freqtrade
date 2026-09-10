"""
ATLAS Trading Service

Keeps paper-trading history.
No live orders.
"""

from datetime import datetime

from atlas.trading.trade_record import TradeRecord


class TradingService:
    """Stores and manages paper-trading history."""

    def __init__(self, repository=None):
        self._repository = repository
        self._history = (
            repository.load()
            if repository is not None
            else []
        )

    def record_buy(
        self,
        symbol,
        quantity,
        price_usd,
        amount_nok,
        reason="",
    ):
        trade = TradeRecord(
            symbol=symbol,
            action="BUY",
            quantity=quantity,
            price_usd=price_usd,
            amount_nok=amount_nok,
            realized_pnl_nok=0.0,
            timestamp=datetime.now(),
            reason=reason,
        )

        self._history.append(trade)

        if self._repository is not None:
            self._repository.save(trade)

        return trade

    def record_sell(
        self,
        symbol,
        quantity,
        price_usd,
        amount_nok,
        realized_pnl_nok,
        reason="",
    ):
        trade = TradeRecord(
            symbol=symbol,
            action="SELL",
            quantity=quantity,
            price_usd=price_usd,
            amount_nok=amount_nok,
            realized_pnl_nok=realized_pnl_nok,
            timestamp=datetime.now(),
            reason=reason,
        )

        self._history.append(trade)

        if self._repository is not None:
            self._repository.save(trade)

        return trade

    def history(self):
        return [
            trade.as_dict()
            for trade in reversed(self._history)
        ]

    def count(self):
        return len(self._history)

    def clear(self):
        self._history.clear()

        if self._repository is not None:
            self._repository.clear()
