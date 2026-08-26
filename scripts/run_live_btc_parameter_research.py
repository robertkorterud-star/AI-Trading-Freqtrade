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
from atlas.trading.strategy_parameter_research import (
    StrategyParameterResearch,
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
    },
    timeframe="4h",
    source="coingecko",
)

data = provider.load(
    symbol="BTC-USD",
)

quality = (
    HistoricalDataQualityValidator()
    .validate(data)
)

print()
print("ATLAS BTC PARAMETER RESEARCH")
print("============================")
print()
print(f"Symbol:     {data.symbol}")
print(f"Timeframe:  {data.timeframe}")
print(f"Source:     {data.source}")
print(f"Candles:    {len(data)}")
print()

print("DATA QUALITY")
print("------------")
print(f"Valid:      {quality.valid}")
print(f"Gaps:       {quality.gap_count}")
print(
    "Coverage:   "
    f"{quality.coverage_ratio_percent:.2f}%"
)
print()

if quality.issues:
    print("Issues:")
    for issue in quality.issues:
        print(f"- {issue}")
    print()

parameter_sets = [
    (3, 10),
    (5, 15),
    (8, 21),
    (10, 30),
    (15, 40),
    (20, 50),
]

research = StrategyParameterResearch(
    transaction_cost_percent=0.1,
    slippage_percent=0.05,
)

result = research.run(
    data,
    parameter_sets=parameter_sets,
    train_size=50,
    test_size=20,
)

print("PARAMETER RESULTS")
print("-----------------")

for item in result.results:

    advantage = (
        item.walk_forward_return_percent
        - item.walk_forward_buy_and_hold_percent
    )

    print(
        f"{item.fast_period:>2}/"
        f"{item.slow_period:<2} | "
        f"BT {item.backtest_return_percent:>7.2f}% | "
        f"WF {item.walk_forward_return_percent:>7.2f}% | "
        f"BH {item.walk_forward_buy_and_hold_percent:>7.2f}% | "
        f"ADV {advantage:>7.2f}% | "
        f"DD {item.max_drawdown_percent:>7.2f}% | "
        f"TRADES {item.trade_count:>2} | "
        f"WINS {item.positive_windows}/"
        f"{item.total_windows} | "
        f"BEAT {item.outperformed_walk_forward}"
    )

print()

best = result.best

if best is None:
    print("BEST: NONE")
else:
    advantage = (
        best.walk_forward_return_percent
        - best.walk_forward_buy_and_hold_percent
    )

    print("BEST PARAMETER SET")
    print("------------------")
    print(
        f"Fast/Slow: "
        f"{best.fast_period}/{best.slow_period}"
    )
    print(
        f"Walk-forward: "
        f"{best.walk_forward_return_percent:.2f}%"
    )
    print(
        f"Buy & Hold: "
        f"{best.walk_forward_buy_and_hold_percent:.2f}%"
    )
    print(
        f"Advantage: "
        f"{advantage:.2f}%"
    )
    print(
        f"Max drawdown: "
        f"{best.max_drawdown_percent:.2f}%"
    )
    print(
        f"Positive windows: "
        f"{best.positive_windows}"
    )
    print(
        f"Negative windows: "
        f"{best.negative_windows}"
    )
    print(
        f"Total windows: "
        f"{best.total_windows}"
    )
    print(
        f"Beat Buy & Hold: "
        f"{best.outperformed_walk_forward}"
    )

print()
