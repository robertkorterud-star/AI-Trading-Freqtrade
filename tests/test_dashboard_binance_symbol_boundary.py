from atlas.dashboard.dashboard_service import DashboardService


def test_dashboard_normalizes_binance_usdt_symbol():
    assert DashboardService._normalize_dashboard_symbol("BTCUSDT") == "BTC-USD"


def test_dashboard_normalizes_binance_usdc_symbol_case_insensitively():
    assert DashboardService._normalize_dashboard_symbol("ethusdc") == "ETH-USD"


def test_dashboard_preserves_existing_symbols():
    assert DashboardService._normalize_dashboard_symbol("BTC-USD") == "BTC-USD"
    assert DashboardService._normalize_dashboard_symbol("NVDA") == "NVDA"
