from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]



def test_market_enhancements_script_is_loaded_by_base_template():
    base = (ROOT / "atlas" / "dashboard" / "templates" / "base.html").read_text()
    assert '/static/market_enhancements.js' in base


def test_market_enhancements_normalize_binance_quote_for_fx():
    script = (ROOT / "atlas" / "dashboard" / "static" / "market_enhancements.js").read_text()
    assert 'source === "USDT" || source === "USDC"' in script
    assert 'url.searchParams.set("source", "USD")' in script


def test_market_research_opens_without_leaving_terminal():
    script = (ROOT / "atlas" / "dashboard" / "static" / "market_enhancements.js").read_text()
    assert '.market-terminal-research' in script
    assert 'event.preventDefault()' in script
    assert '/api/strategy-research?' in script
