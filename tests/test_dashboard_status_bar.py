from pathlib import Path


STATUS_BAR = Path(
    "atlas/dashboard/templates/components/status_bar.html"
)


def test_status_bar_contains_paper_trading_information():

    text = STATUS_BAR.read_text()

    assert "dashboard.trading.mode" in text
    assert "dashboard.trading.paper_trading" in text
    assert "dashboard.trading.virtual_capital_nok" in text
    assert "dashboard.trading.live_orders" in text


def test_status_bar_contains_dynamic_advisor_information():

    text = STATUS_BAR.read_text()

    assert 'dashboard.trading.mode == "advisor"' in text
    assert "ADVISOR MODE" in text
    assert "NO ORDERS" in text
