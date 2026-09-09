from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_watchlist_ui_has_add_remove_and_navigation():
    script = (ROOT / "atlas" / "dashboard" / "static" / "watchlist_ui.js").read_text()
    assert 'STORAGE_KEY = "atlas.watchlist.v1"' in script
    assert "localStorage.getItem" in script
    assert "localStorage.setItem" in script
    assert "watchlist-remove" in script
    assert '"/market/"' in script
    assert "/api/market-search?q=" in script


def test_watchlist_ui_syncs_watchlist_symbols_to_markets_page():
    script = (ROOT / "atlas" / "dashboard" / "static" / "watchlist_ui.js").read_text()
    assert "initMarketsPage" in script
    assert 'window.location.pathname !== "/markets"' in script
    assert "watchlist-market-card" in script
    assert "loadSymbols()" in script
    assert '"/api/market-search?q="' in script
