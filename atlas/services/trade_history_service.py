"""ATLAS trade-history presentation service."""

from datetime import datetime, timedelta

from atlas.trading.trade_record import TradeRecord


class TradeHistoryService:
    """Filter persisted trades and expose chart entry/exit markers."""

    _PERIOD_DURATIONS = {
        "1d": timedelta(days=1),
        "1w": timedelta(weeks=1),
        "1m": timedelta(days=30),
        "3m": timedelta(days=90),
        "6m": timedelta(days=180),
        "1y": timedelta(days=365),
    }

    @staticmethod
    def _normalize_trade(trade):
        """Return a TradeRecord for repository or service history output."""
        if isinstance(trade, TradeRecord):
            return trade
        if isinstance(trade, dict):
            return TradeRecord(
                symbol=trade["symbol"],
                action=trade["action"],
                quantity=float(trade["quantity"]),
                price_usd=float(trade["price_usd"]),
                amount_nok=float(trade["amount_nok"]),
                realized_pnl_nok=float(trade["realized_pnl_nok"]),
                timestamp=(
                    trade["timestamp"]
                    if isinstance(trade["timestamp"], datetime)
                    else datetime.fromisoformat(trade["timestamp"])
                ),
                reason=trade.get("reason", ""),
                analysis_snapshot_id=trade.get("analysis_snapshot_id"),
            )
        raise TypeError(f"Unsupported trade record: {type(trade).__name__}")

    def build(self, trades, period="1d", now=None):
        """Return trades and chart markers for the requested history period."""
        trades = [self._normalize_trade(trade) for trade in trades]
        now = now or datetime.now()

        if period == "all":
            filtered = trades
        else:
            duration = self._PERIOD_DURATIONS.get(period)
            if duration is None:
                raise ValueError(f"Unsupported trade history period: {period}")
            cutoff = now - duration
            filtered = [trade for trade in trades if trade.timestamp >= cutoff]

        filtered = sorted(filtered, key=lambda trade: trade.timestamp)
        markers = [
            {
                "symbol": trade.symbol,
                "action": trade.action,
                "price_usd": trade.price_usd,
                "timestamp": trade.timestamp.isoformat(timespec="seconds"),
            }
            for trade in filtered
        ]

        return {
            "trades": filtered,
            "markers": markers,
        }
