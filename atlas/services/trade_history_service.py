"""ATLAS trade-history presentation service."""

from datetime import datetime, timedelta


class TradeHistoryService:
    """Filter persisted trades and expose chart entry/exit markers."""

    _PERIOD_DURATIONS = {
        "1d": timedelta(days=1),
        "1w": timedelta(weeks=1),
        "1m": timedelta(days=30),
    }

    def build(self, trades, period="1d", now=None):
        """Return trades and chart markers for the requested history period."""
        trades = list(trades)
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
