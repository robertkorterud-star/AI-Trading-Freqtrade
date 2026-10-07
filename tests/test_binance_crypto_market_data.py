from atlas.adapters.binance_crypto_market_data import BinanceCryptoMarketDataProvider


class FakeBinance:
    def get_exchange_info(self):
        return {
            "symbols": [
                {
                    "symbol": "BTCUSDT",
                    "baseAsset": "BTC",
                    "quoteAsset": "USDT",
                    "status": "TRADING",
                    "isSpotTradingAllowed": True,
                },
                {
                    "symbol": "ETHBTC",
                    "baseAsset": "ETH",
                    "quoteAsset": "BTC",
                    "status": "TRADING",
                    "isSpotTradingAllowed": True,
                },
                {
                    "symbol": "OLDUSDT",
                    "baseAsset": "OLD",
                    "quoteAsset": "USDT",
                    "status": "BREAK",
                    "isSpotTradingAllowed": True,
                },
            ]
        }

    def get_24hr_tickers(self):
        return [
            {
                "symbol": "BTCUSDT",
                "lastPrice": "100000",
                "volume": "12",
                "quoteVolume": "1200000",
                "priceChangePercent": "5",
                "bidPrice": "99990",
                "askPrice": "100010",
            },
            {
                "symbol": "ETHBTC",
                "lastPrice": "0.03",
                "volume": "100",
                "quoteVolume": "3",
                "priceChangePercent": "1",
                "bidPrice": "0.029",
                "askPrice": "0.031",
            },
            {
                "symbol": "OLDUSDT",
                "lastPrice": "1",
                "volume": "1000",
                "quoteVolume": "1000",
                "priceChangePercent": "50",
                "bidPrice": "0.99",
                "askPrice": "1.01",
            },
        ]


def test_binance_provider_builds_observation_from_active_usdt_spot_market():
    observations = BinanceCryptoMarketDataProvider(FakeBinance()).get_crypto_observations()

    assert len(observations) == 1
    observation = observations[0]
    assert observation.symbol == "BTC"
    assert observation.price == 100000.0
    assert observation.volume == 1200000.0
    assert observation.average_volume == 1200000.0
    assert observation.change_percent == 5.0
    assert observation.liquid is True
    assert observation.bid_ask_spread_percent == 0.02


def test_binance_provider_skips_invalid_or_zero_quotes():
    class InvalidTickerBinance(FakeBinance):
        def get_24hr_tickers(self):
            return [
                {
                    "symbol": "BTCUSDT",
                    "lastPrice": "0",
                    "quoteVolume": "1200000",
                    "priceChangePercent": "5",
                    "bidPrice": "0",
                    "askPrice": "0",
                }
            ]

    assert BinanceCryptoMarketDataProvider(
        InvalidTickerBinance()
    ).get_crypto_observations() == []
