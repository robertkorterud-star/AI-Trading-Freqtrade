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
    one_hour_symbols = {
        symbol
        for symbol, interval, _ in adapter.klines_calls
        if interval == "1h"
    }
    five_minute_symbols = {
        symbol
        for symbol, interval, _ in adapter.klines_calls
        if interval == "5m"
    }
    assert one_hour_symbols == {"AUSDT", "BUSDT", "CUSDT", "DUSDT"}
    assert five_minute_symbols == {"AUSDT", "BUSDT", "CUSDT", "DUSDT", "EUSDT"}
    assert len(adapter.klines_calls) == 9
    assert all(
        call[2] == (26 if call[1] == "5m" else 25)
        for call in adapter.klines_calls
    )


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
    assert sorted(adapter.klines_calls) == [
        ("BTCUSDT", "1h", 25),
        ("BTCUSDT", "5m", 26),
    ]


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
    assert sorted(adapter.klines_calls) == [
        ("BTCUSDT", "1h", 4),
        ("BTCUSDT", "5m", 5),
    ]


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
    assert sorted(adapter.klines_calls) == [
        ("BTCUSDT", "1h", 25),
        ("BTCUSDT", "5m", 26),
    ]


def test_binance_enrichment_exposes_canonical_atr_percent():
    class VolatilityAdapter(FakeAdapter):
        def get_klines(self, symbol, interval="1h", limit=24):
            self.klines_calls.append((symbol, interval, limit))
            rows = []
            for index in range(limit):
                close = 100.0 + index
                rows.append([
                    index * 3_600_000,
                    str(close - 1.0),
                    str(close + 2.0),
                    str(close - 2.0),
                    str(close),
                    "1000",
                    (index + 1) * 3_600_000 - 1,
                    "1000000",
                ])
            return rows

    tickers = [{
        "symbol": "BTCUSDT",
        "lastPrice": "124",
        "highPrice": "125",
        "lowPrice": "95",
        "quoteVolume": "500000000",
        "priceChangePercent": "2",
    }]
    adapter = VolatilityAdapter(tickers)
    service = BinanceScannerService(
        MarketData(adapter),
        volume_enrichment_limit=1,
    )

    observations = service.observations()

    assert observations[0].atr_percent > 0.0


def test_binance_enrichment_exposes_completed_5m_relative_volume():
    class ShortVolumeAdapter(FakeAdapter):
        def get_klines(self, symbol, interval="1h", limit=24):
            self.klines_calls.append((symbol, interval, limit))

            step_ms = 300_000 if interval == "5m" else 3_600_000
            quote_volumes = (
                [1_000_000] * 24 + [5_000_000, 99_000_000]
                if interval == "5m"
                else [1_000_000] * limit
            )

            rows = []
            for index, quote_volume in enumerate(quote_volumes):
                rows.append([
                    index * step_ms,
                    "100",
                    "101",
                    "99",
                    "100",
                    "1000",
                    (
                        9_999_999_999_999
                        if interval == "5m" and index == len(quote_volumes) - 1
                        else (index + 1) * step_ms - 1
                    ),
                    str(quote_volume),
                ])
            return rows

    tickers = [{
        "symbol": "BTCUSDT",
        "lastPrice": "100",
        "highPrice": "101",
        "lowPrice": "90",
        "quoteVolume": "500000000",
        "priceChangePercent": "2",
    }]

    adapter = ShortVolumeAdapter(tickers)
    service = BinanceScannerService(
        MarketData(adapter),
        volume_enrichment_limit=1,
    )

    observations = service.observations()

    assert observations[0].relative_volume_5m == 5.0
    assert ("BTCUSDT", "5m", 26) in adapter.klines_calls


def test_5m_discovery_can_be_broader_than_deep_volume_enrichment():
    tickers = [
        {
            "symbol": "AUSDT",
            "lastPrice": "10",
            "highPrice": "11",
            "lowPrice": "9",
            "quoteVolume": "5000000",
            "priceChangePercent": "1",
        },
        {
            "symbol": "BUSDT",
            "lastPrice": "10",
            "highPrice": "11",
            "lowPrice": "9",
            "quoteVolume": "4000000",
            "priceChangePercent": "0.5",
        },
    ]
    adapter = FakeAdapter(
        tickers,
        {"AUSDT": 100000, "BUSDT": 100000},
    )
    service = BinanceScannerService(
        MarketData(adapter),
        volume_enrichment_limit=1,
        relative_volume_5m_discovery_limit=2,
    )

    service.observations()

    one_hour_symbols = {
        symbol for symbol, interval, _ in adapter.klines_calls
        if interval == "1h"
    }
    five_minute_symbols = {
        symbol for symbol, interval, _ in adapter.klines_calls
        if interval == "5m"
    }

    assert one_hour_symbols == {"AUSDT"}
    assert five_minute_symbols == {"AUSDT", "BUSDT"}
