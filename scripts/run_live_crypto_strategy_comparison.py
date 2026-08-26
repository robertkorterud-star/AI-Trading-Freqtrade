import requests

from atlas.trading.coingecko_http_client import (
    CoinGeckoHTTPClient,
)
from atlas.trading.coingecko_ohlc import (
    CoinGeckoOHLCProvider,
)
from atlas.trading.historical_data_quality import (
    HistoricalDataQualityValidator,
)
from atlas.trading.historical_strategy_research import (
    HistoricalStrategyResearch,
)
from atlas.trading.mean_reversion_strategy_research import (
    MeanReversionStrategyResearch,
)
from atlas.trading.momentum_strategy_research import (
    MomentumStrategyResearch,
)
from atlas.trading.multi_market_strategy_comparison import (
    MultiMarketStrategyComparison,
    format_multi_market_strategy_comparison,
)


class RequestsTransport:

    def get(
        self,
        url,
        *,
        params,
        timeout,
    ):
        return requests.get(
            url,
            params=params,
            timeout=timeout,
        )


client = CoinGeckoHTTPClient(
    transport=RequestsTransport(),
    timeout=15.0,
)

provider = CoinGeckoOHLCProvider(
    client=client,
    coin_ids={
        "BTC-USD": "bitcoin",
        "ETH-USD": "ethereum",
        "SOL-USD": "solana",
        "XRP-USD": "ripple",
    },
    timeframe="4h",
    source="coingecko",
)

symbols = [
    "BTC-USD",
    "ETH-USD",
    "SOL-USD",
    "XRP-USD",
]

datasets = {}

print()
print("ATLAS LIVE CRYPTO STRATEGY COMPARISON")
print("=====================================")
print()

for symbol in symbols:

    data = provider.load(
        symbol=symbol,
    )

    quality = (
        HistoricalDataQualityValidator()
        .validate(data)
    )

    print(
        f"{symbol:<8} "
        f"bars={len(data):3d} "
        f"gaps={quality.gap_count:2d} "
        f"coverage="
        f"{quality.coverage_ratio_percent:6.2f}% "
        f"valid={quality.valid}"
    )

    if not quality.valid:
        raise RuntimeError(
            f"Invalid historical data: {symbol}"
        )

    datasets[symbol] = data

train_size = 50
test_size = 20

trend_results = {}
mean_reversion_results = {}
momentum_results = {}

for symbol, data in datasets.items():

    trend_results[symbol] = (
        HistoricalStrategyResearch(
            fast_period=5,
            slow_period=15,
            transaction_cost_percent=0.1,
            slippage_percent=0.05,
        ).run(
            data,
            train_size=train_size,
            test_size=test_size,
        )
    )

    mean_reversion_results[symbol] = (
        MeanReversionStrategyResearch(
            lookback_period=20,
            entry_deviation_percent=2.0,
            transaction_cost_percent=0.1,
            slippage_percent=0.05,
        ).run(
            data,
            train_size=train_size,
            test_size=test_size,
        )
    )

    momentum_results[symbol] = (
        MomentumStrategyResearch(
            lookback_period=20,
            transaction_cost_percent=0.1,
            slippage_percent=0.05,
        ).run(
            data,
            train_size=train_size,
            test_size=test_size,
        )
    )

summary = (
    MultiMarketStrategyComparison()
    .compare(
        {
            "Trend Following": trend_results,
            "Mean Reversion": mean_reversion_results,
            "Momentum": momentum_results,
        }
    )
)

print()
print(
    format_multi_market_strategy_comparison(
        summary
    )
)
print()
