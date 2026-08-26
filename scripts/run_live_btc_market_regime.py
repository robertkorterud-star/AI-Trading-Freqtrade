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
from atlas.trading.market_regime_research import (
    MarketRegimeResearch,
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
print("ATLAS LIVE BTC MARKET REGIME RESEARCH")
print("======================================")
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

if not quality.valid:
    print("VERDICT: INVALID DATA")
    raise SystemExit(1)

result = MarketRegimeResearch(
    forward_period=1,
).run(data)

print("REGIME DISTRIBUTION")
print("-------------------")

for regime, count in (
    result.regime_distribution.items()
):
    print(
        f"{regime:18} {count:4}"
    )

print()

print("AVERAGE FORWARD RETURNS")
print("-----------------------")

for regime, value in (
    result.average_forward_returns.items()
):
    print(
        f"{regime:18} "
        f"{value:8.3f}%"
    )

print()

print("RESEARCH SUMMARY")
print("----------------")
print(
    "Classified observations: "
    f"{result.classified_observations}"
)

if result.average_forward_returns:
    best_regime = max(
        result.average_forward_returns,
        key=result.average_forward_returns.get,
    )

    best_return = (
        result.average_forward_returns[
            best_regime
        ]
    )

    print(
        f"Best forward regime: "
        f"{best_regime}"
    )
    print(
        f"Best average return: "
        f"{best_return:.3f}%"
    )
else:
    print("Best forward regime: None")

print()
