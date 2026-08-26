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
from atlas.trading.strategy_comparison import (
    StrategyComparison,
    format_strategy_comparison,
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
print("ATLAS LIVE BTC STRATEGY COMPARISON")
print("==================================")
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

train_size = 50
test_size = 20

trend = HistoricalStrategyResearch(
    fast_period=5,
    slow_period=15,
    transaction_cost_percent=0.1,
    slippage_percent=0.05,
).run(
    data,
    train_size=train_size,
    test_size=test_size,
)

mean_reversion = MeanReversionStrategyResearch(
    lookback_period=20,
    entry_deviation_percent=2.0,
    transaction_cost_percent=0.1,
    slippage_percent=0.05,
).run(
    data,
    train_size=train_size,
    test_size=test_size,
)

momentum = MomentumStrategyResearch(
    lookback_period=20,
    transaction_cost_percent=0.1,
    slippage_percent=0.05,
).run(
    data,
    train_size=train_size,
    test_size=test_size,
)

comparison = StrategyComparison().compare(
    {
        "Trend Following": trend,
        "Mean Reversion": mean_reversion,
        "Momentum": momentum,
    }
)

print()
print(
    format_strategy_comparison(
        comparison
    )
)
print()
