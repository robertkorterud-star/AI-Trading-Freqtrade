from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_watchlist_service_exists():
    assert (ROOT / 'atlas/services/watchlist_service.py').exists()

def test_watchlist_routes_exist():
    text = (ROOT / 'atlas/dashboard/watchlist_routes.py').read_text()
    assert '/api/watchlist' in text

def test_watchlist_ui_exists():
    text = (ROOT / 'atlas/dashboard/static/watchlist_ui.js').read_text()
    assert 'method:"POST"' in text or 'method: "POST"' in text
