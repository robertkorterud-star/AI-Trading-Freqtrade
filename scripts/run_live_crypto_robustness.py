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
from atlas.trading.strategy_robustness_research import (
    StrategyRobustnessResearch,
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

datasets = []

print()
print("ATLAS LIVE CRYPTO ROBUSTNESS")
print("============================")
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
        f"bars={len(data):>3} "
        f"gaps={quality.gap_count:>2} "
        f"coverage="
        f"{quality.coverage_ratio_percent:>6.2f}% "
        f"valid={quality.valid}"
    )

    if not quality.valid:
        print(
            f"Skipping {symbol}: "
            "data quality is invalid."
        )
        continue

    datasets.append(data)

print()

research = StrategyRobustnessResearch(
    transaction_cost_percent=0.1,
    slippage_percent=0.05,
)

result = research.run(
    datasets,
    fast_period=3,
    slow_period=10,
    train_size=50,
    test_size=20,
)

print("ROBUSTNESS RESULTS")
print("------------------")

for item in result.results:

    print(
        f"{item.symbol:<8} "
        f"WF={item.walk_forward_return_percent:>7.2f}% "
        f"BH={item.buy_and_hold_return_percent:>7.2f}% "
        f"ADV={item.advantage_percent:>7.2f}% "
        f"WINS={item.positive_windows}/"
        f"{item.total_windows} "
        f"BEAT={item.outperformed_buy_and_hold}"
    )

print()

print("ROBUSTNESS SUMMARY")
print("------------------")
print(
    f"Datasets tested: "
    f"{result.datasets_tested}"
)
print(
    f"Datasets outperformed: "
    f"{result.datasets_outperformed}"
)
print(
    f"Outperformance ratio: "
    f"{result.outperformance_ratio_percent:.2f}%"
)
print(
    f"Average advantage: "
    f"{result.average_advantage_percent:.2f}%"
)
print(
    f"Robust: "
    f"{result.robust}"
)

if result.best is not None:
    print()
    print("BEST DATASET")
    print("------------")
    print(
        f"Symbol: "
        f"{result.best.symbol}"
    )
    print(
        f"Walk-forward: "
        f"{result.best.walk_forward_return_percent:.2f}%"
    )
    print(
        f"Buy & Hold: "
        f"{result.best.buy_and_hold_return_percent:.2f}%"
    )
    print(
        f"Advantage: "
        f"{result.best.advantage_percent:.2f}%"
    )

print()
