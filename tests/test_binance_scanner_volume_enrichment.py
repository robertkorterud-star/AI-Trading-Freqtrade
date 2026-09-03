from atlas.services.binance_scanner_service import BinanceScannerService


class FakeAdapter:
    def __init__(self, tickers, volumes=None):
        self.tickers = tickers
        self.volumes = volumes or {}
        self.klines_calls = []

    def get_24hr_tickers(self):
        return self.tickers

    def get_klines(self, symbol, interval="1h", limit=24):
        self.klines_calls.append((symbol, interval, limit))
        return [[0, "1", "1", "1", "1", "0", 0, str(self.volumes[symbol])] for _ in range(limit)]


class MarketData:
    def __init__(self, adapter):
        self.adapter = adapter


def test_volume_enrichment_is_bounded_to_volume_and_momentum_shortlists():
    tickers = [
        {"symbol": "AUSDT", "lastPrice": "10", "quoteVolume": "5000000", "priceChangePercent": "1"},
        {"symbol": "BUSDT", "lastPrice": "10", "quoteVolume": "4000000", "priceChangePercent": "2"},
        {"symbol": "CUSDT", "lastPrice": "10", "quoteVolume": "3000000", "priceChangePercent": "20"},
        {"symbol": "DUSDT", "lastPrice": "10", "quoteVolume": "2000000", "priceChangePercent": "15"},
        {"symbol": "EUSDT", "lastPrice": "10", "quoteVolume": "1000000", "priceChangePercent": "3"},
    ]
    adapter = FakeAdapter(
        tickers,
        {symbol: 100000 for symbol in "ABCDE" for _ in [0]},
    )
    service = BinanceScannerService(
        MarketData(adapter),
        volume_enrichment_limit=2,
    )

    observations = service.observations()

    assert len(observations) == 5
    assert {call[0] for call in adapter.klines_calls} == {"AUSDT", "BUSDT", "CUSDT", "DUSDT"}
    assert len(adapter.klines_calls) == 4


def test_historical_volume_is_cached_between_observation_builds():
    tickers = [
        {"symbol": "BTCUSDT", "lastPrice": "100000", "quoteVolume": "500000000", "priceChangePercent": "12"},
    ]
    adapter = FakeAdapter(tickers, {"BTCUSDT": 2500000})
    service = BinanceScannerService(MarketData(adapter), volume_enrichment_limit=1)

    first = service.observations()
    second = service.observations()

    assert first[0].average_volume == 2500000
    assert second[0].average_volume == 2500000
    assert adapter.klines_calls == [("BTCUSDT", "1h", 24)]


def test_historical_volume_uses_binance_quote_volume_field():
    tickers = [
        {"symbol": "BTCUSDT", "lastPrice": "100000", "quoteVolume": "500000000", "priceChangePercent": "12"},
    ]
    adapter = FakeAdapter(tickers, {"BTCUSDT": 1000000})
    service = BinanceScannerService(MarketData(adapter), volume_enrichment_limit=1, volume_samples=3)

    observations = service.observations()

    assert observations[0].average_volume == 1000000
    assert adapter.klines_calls == [("BTCUSDT", "1h", 3)]


def test_failed_volume_enrichment_falls_back_to_current_volume():
    class FailingAdapter(FakeAdapter):
        def get_klines(self, symbol, interval="1h", limit=24):
            self.klines_calls.append((symbol, interval, limit))
            raise RuntimeError("temporary Binance failure")

    tickers = [
        {"symbol": "BTCUSDT", "lastPrice": "100000", "quoteVolume": "500000000", "priceChangePercent": "12"},
    ]
    adapter = FailingAdapter(tickers)
    service = BinanceScannerService(MarketData(adapter), volume_enrichment_limit=1)

    observations = service.observations()

    assert observations[0].average_volume == observations[0].volume
