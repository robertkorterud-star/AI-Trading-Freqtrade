from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_watchlist_service_exists():
    assert (ROOT / "atlas/services/watchlist_service.py").exists()


def test_watchlist_routes_exist():
    text = (ROOT / "atlas/dashboard/watchlist_routes.py").read_text()
    assert "/api/watchlist" in text


def test_watchlist_ui_is_user_managed_and_persistent():
    text = (ROOT / "atlas/dashboard/static/watchlist_ui.js").read_text()
    assert "localStorage" in text
    assert "STORAGE_KEY" in text
    assert "Legg til" in text
    assert "watchlist-remove" in text
    assert "/api/market-search?q=" in text


def test_base_template_loads_watchlist_ui():
    text = (ROOT / "atlas/dashboard/templates/base.html").read_text()
    assert "/static/watchlist_ui.js" in text
