from atlas.adapters.binance_market_data import BinanceMarketDataAdapter
from atlas.services.binance_scanner_service import BinanceScannerService


class FakeBinanceAdapter:
    def get_24hr_tickers(self):
        return [
            {
                "symbol": "BTCUSDT",
                "lastPrice": "100000",
                "quoteVolume": "500000000",
                "priceChangePercent": "12.0",
            },
            {
                "symbol": "ETHUSDT",
                "lastPrice": "4000",
                "quoteVolume": "250000000",
                "priceChangePercent": "4.0",
            },
            {
                "symbol": "FOOUSDT",
                "lastPrice": "1",
                "quoteVolume": "50000",
                "priceChangePercent": "50",
            },
            {
                "symbol": "BTCEUR",
                "lastPrice": "90000",
                "quoteVolume": "999999999",
                "priceChangePercent": "50",
            },
            {"symbol": "BROKENUSDT", "lastPrice": "bad", "quoteVolume": "1"},
        ]


def test_binance_adapter_exposes_all_24h_tickers():
    adapter = BinanceMarketDataAdapter(adapter=FakeBinanceAdapter())

    assert len(adapter.adapter.get_24hr_tickers()) == 5


def test_binance_scanner_builds_crypto_observations_and_filters_universe():
    service = BinanceScannerService(
        BinanceMarketDataAdapter(adapter=FakeBinanceAdapter()),
    )

    observations = service.observations()

    assert [item.symbol for item in observations] == ["BTCUSDT", "ETHUSDT"]
    assert all(item.asset_type.value == "crypto" for item in observations)


def test_binance_scanner_returns_ranked_candidates():
    service = BinanceScannerService(
        BinanceMarketDataAdapter(adapter=FakeBinanceAdapter()),
    )

    result = service.scan(limit=1)

    assert result.scanned == 2
    assert result.eligible == 2
    assert len(result.candidates) == 1
    assert result.candidates[0].symbol == "BTCUSDT"
    assert result.candidates[0].score > result.candidates[0].momentum_score
