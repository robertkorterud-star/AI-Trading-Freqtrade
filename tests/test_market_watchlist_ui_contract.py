from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_market_watchlist_control_uses_shared_storage_and_toggle():
    script = (
        ROOT
        / "atlas"
        / "dashboard"
        / "static"
        / "watchlist_ui.js"
    ).read_text()

    assert 'STORAGE_KEY = "atlas.watchlist.v1"' in script
    assert 'window.location.pathname.startsWith(MARKET_PATH)' in script
    assert 'document.querySelector(".market-terminal-actions")' in script
    assert 'className = "market-watchlist-toggle"' in script
    assert 'button.classList.toggle("is-active", active)' in script
    assert 'saveSymbols(symbols)' in script
    assert 'button.textContent = active ? "★ Watchlist" : "☆ Watchlist";' in script
