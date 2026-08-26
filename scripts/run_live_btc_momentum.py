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
from atlas.trading.momentum_strategy_research import (
    MomentumStrategyResearch,
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
print("ATLAS LIVE BTC MOMENTUM")
print("=======================")
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

if not quality.valid:
    raise RuntimeError(
        "Historical data quality is invalid."
    )

research = MomentumStrategyResearch(
    lookback_period=20,
    transaction_cost_percent=0.1,
    slippage_percent=0.05,
)

result = research.run(
    data,
    train_size=50,
    test_size=20,
)

print("BACKTEST")
print("--------")
print(
    "Strategy return: "
    f"{result.backtest.strategy_return_percent:.2f}%"
)
print(
    "Buy & Hold:      "
    f"{result.backtest.buy_and_hold_return_percent:.2f}%"
)
print(
    "Max drawdown:    "
    f"{result.backtest.max_drawdown_percent:.2f}%"
)
print(
    f"Trades:          "
    f"{result.backtest.trade_count}"
)
print(
    "Win rate:        "
    f"{result.backtest.win_rate_percent:.2f}%"
)
print()

print("WALK-FORWARD")
print("------------")
print(
    "Strategy return: "
    f"{result.strategy_return_percent:.2f}%"
)
print(
    "Buy & Hold:      "
    f"{result.buy_and_hold_return_percent:.2f}%"
)
print(
    "Advantage:       "
    f"{result.advantage_percent:.2f}%"
)
print(
    "Positive windows:"
    f" {result.walk_forward.positive_windows}"
)
print(
    "Negative windows:"
    f" {result.walk_forward.negative_windows}"
)
print(
    "Total windows:   "
    f"{len(result.walk_forward.windows)}"
)
print()

print(
    "Outperformed Buy & Hold: "
    f"{result.outperformed_buy_and_hold}"
)
print(
    f"VERDICT: {result.verdict}"
)
print()
