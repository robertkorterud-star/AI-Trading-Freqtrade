from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_navigation_places_logo_and_menu_on_one_row():
    navbar = (ROOT / "atlas" / "dashboard" / "templates" / "components" / "navbar.html").read_text()
    assert '<nav class="navbar">' in navbar
    assert '<div class="logo">' in navbar
    assert '<div class="menu">' in navbar


def test_dashboard_chart_controls_keep_period_and_interval_consistent():
    template = (ROOT / "atlas" / "dashboard" / "templates" / "index.html").read_text()
    assert "const periodPresets=" in template
    assert "'1d':{interval:'5m',limit:288}" in template
    assert "'5d':{interval:'15m',limit:480}" in template
    assert "'1m':{interval:'1h',limit:720}" in template
    assert "'3m':{interval:'4h',limit:540}" in template
    assert "'6m':{interval:'1d',limit:180}" in template
    assert "'1y':{interval:'1d',limit:365}" in template
    assert "syncIntervalToPeriod" in template
    assert "syncPeriodToInterval" in template
    assert "&limit='+encodeURIComponent(preset.limit)" in template
    assert "status.textContent=symbol+' · '+period.toUpperCase()+' · '+interval" in template


def test_dashboard_styles_add_nav_spacing_and_paragraph_air():
    css = (ROOT / "atlas" / "dashboard" / "static" / "overview.css").read_text()
    assert ".navbar" in css
    assert ".overview-page p" in css
    assert "line-height:1.7" in css
