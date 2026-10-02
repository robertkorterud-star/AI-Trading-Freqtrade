from atlas.adapters.binance_market_data import BinanceMarketDataAdapter
from atlas.services.binance_scanner_service import BinanceScannerService


class FakeBinanceAdapter:
    def get_exchange_info(self, symbol=None):
        symbols = [
            {
                "symbol": ticker["symbol"],
                "status": "TRADING",
                "isSpotTradingAllowed": True,
            }
            for ticker in self.get_24hr_tickers()
            if str(ticker.get("symbol", "")).endswith(("USDT", "USDC"))
        ]
        if symbol is not None:
            symbols = [
                market for market in symbols
                if market["symbol"] == symbol
            ]
        return {"symbols": symbols}

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
    assert 0.0 < result.candidates[0].score < result.candidates[0].momentum_score
    assert "strong daily momentum" in result.candidates[0].reasons


def test_binance_scanner_enrichment_balances_volume_and_momentum():
    service = BinanceScannerService(
        BinanceMarketDataAdapter(adapter=FakeBinanceAdapter()),
        volume_enrichment_limit=1,
    )

    eligible = [
        ("VOLUMEUSDT", 10.0, 10_000_000.0, 1.0, 0.50),
        ("MOMENTUMUSDT", 10.0, 1_000_000.0, 12.0, 0.40),
        ("CALMUSDT", 10.0, 500_000.0, 0.5, 0.30),
    ]

    selected = service._select_volume_enrichment_symbols(eligible)

    assert selected == {"VOLUMEUSDT", "MOMENTUMUSDT"}


def test_enrichment_includes_candidate_near_24h_high():
    service = BinanceScannerService(
        BinanceMarketDataAdapter(adapter=FakeBinanceAdapter()),
        volume_enrichment_limit=1,
    )

    eligible = [
        ("VOLUMEUSDT", 10.0, 10_000_000.0, 1.0, 0.50),
        ("MOMENTUMUSDT", 10.0, 1_000_000.0, 12.0, 0.60),
        ("EARLYUSDT", 10.0, 500_000.0, 1.0, 0.98),
    ]

    selected = service._select_volume_enrichment_symbols(eligible)

    assert selected == {
        "VOLUMEUSDT",
        "MOMENTUMUSDT",
        "EARLYUSDT",
    }


def test_observations_uses_24h_range_position_for_enrichment_selection():
    class RangeFakeBinanceAdapter(FakeBinanceAdapter):
        def get_24hr_tickers(self):
            return [
                {
                    "symbol": "VOLUMEUSDT",
                    "lastPrice": "50",
                    "highPrice": "100",
                    "lowPrice": "0",
                    "quoteVolume": "10000000",
                    "priceChangePercent": "1",
                },
                {
                    "symbol": "MOMENTUMUSDT",
                    "lastPrice": "60",
                    "highPrice": "100",
                    "lowPrice": "0",
                    "quoteVolume": "1000000",
                    "priceChangePercent": "12",
                },
                {
                    "symbol": "EARLYUSDT",
                    "lastPrice": "98",
                    "highPrice": "100",
                    "lowPrice": "0",
                    "quoteVolume": "500000",
                    "priceChangePercent": "1",
                },
            ]

    service = BinanceScannerService(
        BinanceMarketDataAdapter(adapter=RangeFakeBinanceAdapter()),
        volume_enrichment_limit=1,
    )

    selected = set()
    service._enrich_volume_data = lambda symbols: selected.update(symbols) or {}

    observations = service.observations()

    assert [item.symbol for item in observations] == [
        "VOLUMEUSDT",
        "MOMENTUMUSDT",
        "EARLYUSDT",
    ]
    assert selected == {
        "VOLUMEUSDT",
        "MOMENTUMUSDT",
        "EARLYUSDT",
    }


def test_binance_scanner_excludes_markets_not_currently_trading():
    class MarketStatusAdapter(FakeBinanceAdapter):
        def get_24hr_tickers(self):
            return [
                {
                    "symbol": "BTCUSDT",
                    "lastPrice": "100000",
                    "quoteVolume": "500000000",
                    "priceChangePercent": "2",
                },
                {
                    "symbol": "CREAMUSDT",
                    "lastPrice": "10",
                    "quoteVolume": "5000000",
                    "priceChangePercent": "65",
                },
            ]

        def get_exchange_info(self, symbol=None):
            return {
                "symbols": [
                    {
                        "symbol": "BTCUSDT",
                        "status": "TRADING",
                        "isSpotTradingAllowed": True,
                    },
                    {
                        "symbol": "CREAMUSDT",
                        "status": "BREAK",
                        "isSpotTradingAllowed": True,
                    },
                ]
            }

    service = BinanceScannerService(
        BinanceMarketDataAdapter(adapter=MarketStatusAdapter()),
        volume_enrichment_limit=0,
        relative_volume_5m_discovery_limit=0,
    )

    observations = service.observations()

    assert [item.symbol for item in observations] == ["BTCUSDT"]


def test_binance_scanner_enriches_market_cap_from_crypto_metadata():
    class FakeCryptoMetadata:
        def get_markets(self, **kwargs):
            return [
                {
                    "id": "bitcoin",
                    "symbol": "btc",
                    "market_cap": 2_000_000_000_000,
                },
                {
                    "id": "ethereum",
                    "symbol": "eth",
                    "market_cap": 500_000_000_000,
                },
            ]

    service = BinanceScannerService(
        BinanceMarketDataAdapter(adapter=FakeBinanceAdapter()),
        volume_enrichment_limit=0,
        relative_volume_5m_discovery_limit=0,
        spread_enrichment_limit=0,
        crypto_metadata=FakeCryptoMetadata(),
    )

    observations = service.observations()
    by_symbol = {item.symbol: item for item in observations}

    assert by_symbol["BTCUSDT"].market_cap == 2_000_000_000_000
    assert by_symbol["ETHUSDT"].market_cap == 500_000_000_000


def test_binance_scanner_market_cap_enrichment_fails_open():
    class FailingCryptoMetadata:
        def get_markets(self, **kwargs):
            raise RuntimeError("CoinGecko unavailable")

    service = BinanceScannerService(
        BinanceMarketDataAdapter(adapter=FakeBinanceAdapter()),
        volume_enrichment_limit=0,
        relative_volume_5m_discovery_limit=0,
        spread_enrichment_limit=0,
        crypto_metadata=FailingCryptoMetadata(),
    )

    observations = service.observations()

    assert [item.symbol for item in observations] == ["BTCUSDT", "ETHUSDT"]
    assert all(item.market_cap is None for item in observations)


def test_binance_scanner_does_not_guess_market_cap_for_duplicate_crypto_symbol():
    class DuplicateCryptoMetadata:
        def get_markets(self, **kwargs):
            return [
                {
                    "id": "foo-one",
                    "symbol": "btc",
                    "market_cap": 1_000_000,
                },
                {
                    "id": "foo-two",
                    "symbol": "btc",
                    "market_cap": 9_000_000,
                },
            ]

    service = BinanceScannerService(
        BinanceMarketDataAdapter(adapter=FakeBinanceAdapter()),
        volume_enrichment_limit=0,
        relative_volume_5m_discovery_limit=0,
        spread_enrichment_limit=0,
        crypto_metadata=DuplicateCryptoMetadata(),
    )

    observations = service.observations()
    by_symbol = {item.symbol: item for item in observations}

    assert by_symbol["BTCUSDT"].market_cap is None


def test_binance_scanner_market_cap_enrichment_reads_later_pages():
    class PaginatedCryptoMetadata:
        def __init__(self):
            self.calls = []

        def get_markets(self, **kwargs):
            self.calls.append(kwargs)
            if kwargs.get("page", 1) == 1:
                return [
                    {
                        "id": "bitcoin",
                        "symbol": "btc",
                        "market_cap": 2_000_000_000_000,
                    },
                ]
            if kwargs["page"] == 2:
                return [
                    {
                        "id": "ethereum",
                        "symbol": "eth",
                        "market_cap": 500_000_000_000,
                    },
                ]
            return []

    metadata = PaginatedCryptoMetadata()
    service = BinanceScannerService(
        BinanceMarketDataAdapter(adapter=FakeBinanceAdapter()),
        volume_enrichment_limit=0,
        relative_volume_5m_discovery_limit=0,
        spread_enrichment_limit=0,
        crypto_metadata=metadata,
    )

    observations = service.observations()
    by_symbol = {item.symbol: item for item in observations}

    assert by_symbol["BTCUSDT"].market_cap == 2_000_000_000_000
    assert by_symbol["ETHUSDT"].market_cap == 500_000_000_000
    assert any(call.get("page") == 2 for call in metadata.calls)
