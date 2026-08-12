from pathlib import Path


SETTINGS_TEMPLATE = Path(
    "atlas/dashboard/templates/settings.html"
)


def test_settings_page_contains_trading_mode_controls():

    text = SETTINGS_TEMPLATE.read_text()

    assert "Trading Mode" in text
    assert "Advisor" in text
    assert "Paper / Dry Run" in text
    assert "paper_trading" in text


def test_settings_page_uses_active_trading_mode():

    text = SETTINGS_TEMPLATE.read_text()

    assert "dashboard.trading.mode" in text
    assert "dashboard.trading.paper_trading" in text


def test_settings_page_contains_save_form():

    text = SETTINGS_TEMPLATE.read_text()

    assert '<form' in text
    assert 'action="/settings"' in text
    assert 'method="post"' in text
    assert 'Save Settings' in text


def test_settings_page_marks_active_trading_mode():

    text = SETTINGS_TEMPLATE.read_text()

    assert 'value="advisor"' in text
    assert 'value="paper"' in text
    assert 'dashboard.trading.mode == "advisor"' in text
    assert 'dashboard.trading.mode == "paper"' in text
