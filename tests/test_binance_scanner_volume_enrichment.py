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
        values = self.volumes[symbol]
        if isinstance(values, (list, tuple)):
            return [[0, "1", "1", "1", "1", "0", 0, str(value)] for value in values]
        return [[0, "1", "1", "1", "1", "0", 0, str(values)] for _ in range(limit)]


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
        {f"{symbol}USDT": 100000 for symbol in "ABCDE"},
    )
    service = BinanceScannerService(
        MarketData(adapter),
        volume_enrichment_limit=2,
    )

    observations = service.observations()

    assert len(observations) == 5
    assert {call[0] for call in adapter.klines_calls} == {"AUSDT", "BUSDT", "CUSDT", "DUSDT"}
    assert len(adapter.klines_calls) == 4
    assert all(call[2] == 25 for call in adapter.klines_calls)


def test_historical_volume_is_cached_between_observation_builds():
    tickers = [
        {"symbol": "BTCUSDT", "lastPrice": "100000", "quoteVolume": "500000000", "priceChangePercent": "12"},
    ]
    adapter = FakeAdapter(tickers, {"BTCUSDT": 2500000})
    service = BinanceScannerService(MarketData(adapter), volume_enrichment_limit=1)

    first = service.observations()
    second = service.observations()

    assert first[0].average_volume == 2500000
    assert first[0].volume == 2500000
    assert second[0].average_volume == 2500000
    assert second[0].volume == 2500000
    assert adapter.klines_calls == [("BTCUSDT", "1h", 25)]


def test_scanner_volume_uses_current_completed_1h_against_previous_average():
    tickers = [
        {"symbol": "BTCUSDT", "lastPrice": "100000", "quoteVolume": "500000000", "priceChangePercent": "12"},
    ]
    adapter = FakeAdapter(
        tickers,
        {"BTCUSDT": [1_000_000] * 24 + [5_000_000]},
    )
    service = BinanceScannerService(MarketData(adapter), volume_enrichment_limit=1)

    observations = service.observations()

    assert observations[0].volume == 5_000_000
    assert observations[0].average_volume == 1_000_000
    assert observations[0].volume / observations[0].average_volume == 5.0


def test_binance_enrichment_calculates_breakout_above_previous_24h_high():
    class BreakoutAdapter(FakeAdapter):
        def get_klines(self, symbol, interval="1h", limit=24):
            self.klines_calls.append((symbol, interval, limit))
            rows = []
            for _ in range(limit - 1):
                rows.append([0, "95", "100", "90", "98", "0", 0, "1000000"])
            rows.append([0, "100", "106", "99", "106", "0", 0, "5000000"])
            return rows

    tickers = [
        {"symbol": "BTCUSDT", "lastPrice": "106", "quoteVolume": "500000000", "priceChangePercent": "8"},
    ]
    adapter = BreakoutAdapter(tickers)
    service = BinanceScannerService(MarketData(adapter), volume_enrichment_limit=1)

    observations = service.observations()

    assert observations[0].breakout_percent == 6.0
    assert observations[0].volume == 5_000_000
    assert observations[0].average_volume == 1_000_000


def test_historical_volume_uses_binance_quote_volume_field():
    tickers = [
        {"symbol": "BTCUSDT", "lastPrice": "100000", "quoteVolume": "500000000", "priceChangePercent": "12"},
    ]
    adapter = FakeAdapter(tickers, {"BTCUSDT": 1000000})
    service = BinanceScannerService(MarketData(adapter), volume_enrichment_limit=1, volume_samples=3)

    observations = service.observations()

    assert observations[0].average_volume == 1000000
    assert observations[0].volume == 1000000
    assert adapter.klines_calls == [("BTCUSDT", "1h", 4)]


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
    assert adapter.klines_calls == [("BTCUSDT", "1h", 25)]
