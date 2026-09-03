from atlas.services.watchlist_service import WatchlistService


def test_watchlist_defaults_and_persists(tmp_path):
    service = WatchlistService(tmp_path / "watchlist.json")
    assert service.get() == ["BTC-USD", "ETH-USD", "SOL-USD", "NVDA"]
    assert service.add("AAPL")[-1] == "AAPL"
    assert WatchlistService(tmp_path / "watchlist.json").get()[-1] == "AAPL"


def test_watchlist_normalizes_binance_symbols(tmp_path):
    service = WatchlistService(tmp_path / "watchlist.json")
    service.get()
    service.add("DOGEUSDT")
    assert "DOGE-USD" in service.get()
    service.remove("DOGE-USD")
    assert "DOGE-USD" not in service.get()
