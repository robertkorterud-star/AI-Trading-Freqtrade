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
from atlas.trading.strategy_research_report import (
    format_research_report,
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
print("ATLAS LIVE BTC RESEARCH")
print("=======================")
print()
print(f"Symbol:     {data.symbol}")
print(f"Timeframe:  {data.timeframe}")
print(f"Source:     {data.source}")
print(f"Candles:    {len(data)}")
print(f"Start:      {data.start}")
print(f"End:        {data.end}")
print()

print("DATA QUALITY")
print("------------")
print(f"Valid:      {quality.valid}")
print(f"Bars:       {quality.bar_count}")
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

research = HistoricalStrategyResearch(
    fast_period=5,
    slow_period=15,
    transaction_cost_percent=0.1,
    slippage_percent=0.05,
)

result = research.run(
    data,
    train_size=50,
    test_size=20,
)

print(format_research_report(result.report))
print()

print("RESEARCH METADATA")
print("-----------------")
print(
    "Data quality: "
    f"{result.quality.valid}"
)
print(
    "Data coverage: "
    f"{result.quality.coverage_ratio_percent:.2f}%"
)
print(
    "Backtest trades: "
    f"{result.backtest.trade_count}"
)
print(
    "Walk-forward windows: "
    f"{len(result.walk_forward.windows)}"
)
print()


if __name__ == "__main__":
    pass
