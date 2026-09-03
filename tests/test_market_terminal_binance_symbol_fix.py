from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_market_terminal_fix_is_loaded():
    base = (ROOT / "atlas" / "dashboard" / "templates" / "base.html").read_text()
    assert '/static/market_terminal_fix.js' in base


def test_market_terminal_fix_maps_yahoo_crypto_symbols_to_binance():
    script = (ROOT / "atlas" / "dashboard" / "static" / "market_terminal_fix.js").read_text()
    assert 'value.slice(0, -4) + "USDT"' in script
    assert '/api/binance-candles' in script
