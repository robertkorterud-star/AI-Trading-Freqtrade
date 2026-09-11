from datetime import datetime, timedelta

from atlas.services.trade_history_service import TradeHistoryService
from atlas.trading.trade_record import TradeRecord


def _trade(symbol, action, timestamp, price, pnl=0.0):
    return TradeRecord(symbol=symbol, action=action, quantity=1.0, price_usd=price, amount_nok=price, realized_pnl_nok=pnl, timestamp=timestamp, reason="test")


def test_trade_history_builds_entry_and_exit_markers():
    now = datetime(2026, 9, 11, 12, 0, 0)
    trades = [_trade("XRP-USD", "BUY", now - timedelta(hours=2), 1.34), _trade("XRP-USD", "SELL", now - timedelta(hours=1), 1.39, pnl=0.05)]
    history = TradeHistoryService().build(trades, period="1d", now=now)
    assert history["markers"] == [
        {"symbol": "XRP-USD", "action": "BUY", "price_usd": 1.34, "timestamp": (now - timedelta(hours=2)).isoformat(timespec="seconds")},
        {"symbol": "XRP-USD", "action": "SELL", "price_usd": 1.39, "timestamp": (now - timedelta(hours=1)).isoformat(timespec="seconds")},
    ]


def test_trade_history_filters_by_period_without_changing_trade_data():
    now = datetime(2026, 9, 11, 12, 0, 0)
    recent = _trade("BTC-USD", "BUY", now - timedelta(days=2), 100000)
    old = _trade("ETH-USD", "BUY", now - timedelta(days=10), 4000)
    history = TradeHistoryService().build([old, recent], period="1w", now=now)
    assert history["trades"] == [recent]


def test_trade_history_supports_all_period():
    now = datetime(2026, 9, 11, 12, 0, 0)
    trades = [_trade("BTC-USD", "BUY", now - timedelta(days=365), 100000), _trade("ETH-USD", "SELL", now - timedelta(days=10), 4000)]
    history = TradeHistoryService().build(trades, period="all", now=now)
    assert history["trades"] == trades


def test_trade_history_handles_empty_history():
    assert TradeHistoryService().build([], period="1m") == {"trades": [], "markers": []}
