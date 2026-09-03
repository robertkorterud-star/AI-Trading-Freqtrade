from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_watchlist_ui_has_add_remove_and_navigation():
    script = (ROOT / "atlas" / "dashboard" / "static" / "watchlist_ui.js").read_text()
    assert "/api/watchlist" in script
    assert 'method: "DELETE"' in script
    assert 'method: "POST"' in script
    assert '"/market/"' in script
