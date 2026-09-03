from atlas.adapters.historical_market_data import HistoricalMarketDataAdapter


def test_normalize_symbol_maps_usd_fx_aliases():
    adapter = HistoricalMarketDataAdapter()

    assert adapter._normalize_symbol("USDNOK=X") == "NOK=X"
    assert adapter._normalize_symbol("USDDKK=X") == "DKK=X"
    assert adapter._normalize_symbol("USDSEK=X") == "SEK=X"
    assert adapter._normalize_symbol("USDEUR=X") == "EUR=X"


def test_normalize_symbol_keeps_regular_symbols_unchanged():
    adapter = HistoricalMarketDataAdapter()

    assert adapter._normalize_symbol("AAPL") == "AAPL"
    assert adapter._normalize_symbol("sol-usd") == "SOL-USD"
