from pathlib import Path


TEMPLATE = Path("atlas/dashboard/templates/portfolio.html")


def test_portfolio_template_uses_canonical_dashboard_state():
    template = TEMPLATE.read_text(encoding="utf-8")

    assert "dashboard.portfolio.total_equity_nok" in template
    assert "dashboard.trade_history" in template
    assert "/static/paper_portfolio.json" not in template
    assert "/static/virtual_trades.json" not in template
    assert "ATLAS Dry-Run handler" not in template
