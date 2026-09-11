from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_navigation_places_logo_and_menu_on_one_row():
    navbar = (ROOT / "atlas" / "dashboard" / "templates" / "components" / "navbar.html").read_text()
    assert '<nav class="navbar">' in navbar
    assert '<div class="logo">' in navbar
    assert '<div class="menu">' in navbar


def test_dashboard_chart_controls_keep_period_and_interval_consistent():
    template = (ROOT / "atlas" / "dashboard" / "templates" / "index.html").read_text()

    assert "const periodConfig=" in template
    assert "'1d':{period:'1d',interval:'5m'}" in template
    assert "'1w':{period:'5d',interval:'15m'}" in template
    assert "'1m':{period:'1m',interval:'1h'}" in template
    assert "'all':{period:'5y',interval:'1d'}" in template
    assert "const initialPeriod=" in template
    assert "trade_history_period" in template
    assert "encodeURIComponent(cfg.period)" in template
    assert "encodeURIComponent(cfg.interval)" in template
    assert "status.textContent=symbol+' · '+period.toUpperCase()" in template
    assert "BUY/SELL-markører viser faktiske ATLAS-handler" in template


def test_dashboard_styles_add_nav_spacing_and_paragraph_air():
    css = (ROOT / "atlas" / "dashboard" / "static" / "overview.css").read_text()
    assert ".navbar" in css
    assert ".overview-page p" in css
    assert "line-height:1.7" in css
