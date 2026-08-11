from pathlib import Path


STYLE = Path(
    "atlas/dashboard/static/style.css"
)


def test_dashboard_has_paper_trading_status_style():

    text = STYLE.read_text()

    assert ".paper-status" in text
    assert ".paper-status .status-dot" in text
