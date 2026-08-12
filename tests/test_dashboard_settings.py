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
